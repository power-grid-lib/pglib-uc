# Tested with Julia v1.1, JSON v0.21, JuMP v0.19, Cbc v0.6

using JSON
using JuMP


println("loading data")

## Grab instance file from first command line argument
data_file = ARGS[1]
data = JSON.parsefile(data_file)


println("model building")

thermal_gens = keys(data["thermal_generators"])
renewable_gens = keys(data["renewable_generators"])
time_periods = 1:data["time_periods"]

gen_startup_categories = Dict(g => 1:length(gen["startup"]) for (g,gen) in data["thermal_generators"])
gen_pwl_points = Dict(g => 1:length(gen["piecewise_production"]) for (g,gen) in data["thermal_generators"])

m = Model()

@variable(m, cg[thermal_gens,time_periods])
@variable(m, pg[thermal_gens,time_periods] >= 0)
@variable(m, pw[renewable_gens,time_periods] >= 0)
@variable(m, rg[thermal_gens,time_periods] >= 0)
@variable(m, ug[thermal_gens,time_periods], binary=true)
@variable(m, vg[thermal_gens,time_periods], binary=true)
@variable(m, wg[thermal_gens,time_periods], binary=true)
@variable(m, delta_sg[g in thermal_gens,gen_startup_categories[g],time_periods], binary=true)
@variable(m, 0 <= lambda_lg[g in thermal_gens,gen_pwl_points[g],time_periods] <= 1)


@objective(m, Min,
    sum(
        sum(
            cg[g,t] + gen["piecewise_production"][1]["cost"]*ug[g,t] +
            sum(
                gen_startup["cost"]*delta_sg[g,i,t]
            for (i, gen_startup) in enumerate(gen["startup"]))
        for t in time_periods)
    for (g, gen) in data["thermal_generators"])
) # (1)

for (g, gen) in data["thermal_generators"]

    if gen["unit_on_t0"] == 1
        @constraint(m, sum( (ug[g,t]-1) for t in 1:min(data["time_periods"], gen["time_up_minimum"] - gen["time_up_t0"]) ) == 0) # (4)
    else
        @constraint(m, sum( ug[g,t] for t in 1:min(data["time_periods"], gen["time_down_minimum"] - gen["time_down_t0"]) ) == 0) # (5)
    end

    @constraint(m, ug[g,1] - gen["unit_on_t0"] == vg[g,1] - wg[g,1]) # (6)

    @constraint(m, 0 ==
        sum(
            sum(
                delta_sg[g,i,t]
            for t in max(1, gen["startup"][i+1]["lag"] - gen["time_down_t0"] + 1):min(gen["startup"][i+1]["lag"]-1, data["time_periods"]))
        for (i,startup) in enumerate(gen["startup"][1:end-1]))
    ) # (7)

    @constraint(m, pg[g,1] + rg[g,1] - gen["unit_on_t0"]*(gen["power_output_t0"] - gen["power_output_minimum"]) <= gen["ramp_up_limit"]) # (8)
    @constraint(m, gen["unit_on_t0"]*(gen["power_output_t0"] - gen["power_output_minimum"]) - pg[g,1] <= gen["ramp_down_limit"]) # (9)
    @constraint(m, gen["unit_on_t0"]*(gen["power_output_t0"] - gen["power_output_minimum"]) <= gen["unit_on_t0"]*(gen["power_output_maximum"] - gen["power_output_minimum"]) - max(0, gen["power_output_maximum"] - gen["ramp_shutdown_limit"])*wg[g,1]) # (10)
end

for t in time_periods
    @constraint(m, 
        sum( pg[g,t] + gen["power_output_minimum"]*ug[g,t] for (g, gen) in data["thermal_generators"] ) +
        sum( pw[g,t] for g in renewable_gens)
        == data["demand"][t]
    ) # (2)

    @constraint(m, sum(rg[g,t] for g in thermal_gens) >= data["reserves"][t]) # (3)

    for (g, gen) in data["thermal_generators"]

        @constraint(m, ug[g,t] >= gen["must_run"]) # (11)

        if t > 1
            @constraint(m, ug[g,t] - ug[g,t-1] == vg[g,t] - wg[g,t]) # (12)
            @constraint(m, pg[g,t] + rg[g,t] - pg[g,t-1] <= gen["ramp_up_limit"]) # (19)
            @constraint(m, pg[g,t-1] - pg[g,t] <= gen["ramp_down_limit"]) # (20)
        end


        if t >= gen["time_up_minimum"] || t == data["time_periods"]
            @constraint(m, sum( vg[g,t2] for t2 in (t-min(gen["time_up_minimum"],data["time_periods"])+1):t) <= ug[g,t])  # (13)
        end

        if t >= gen["time_down_minimum"] || t == data["time_periods"]
            @constraint(m, sum( wg[g,t2] for t2 in (t-min(gen["time_down_minimum"],data["time_periods"])+1):t) <= 1 - ug[g,t])  # (14)
        end

        for (si,startup) in enumerate(gen["startup"][1:end-1])
            if t >= gen["startup"][si+1]["lag"]
                time_range = startup["lag"]:(gen["startup"][si+1]["lag"]-1)
                @constraint(m, delta_sg[g,si,t] <= sum(wg[g,t-i] for i in time_range)) # (15)
            end
        end

        @constraint(m, vg[g,t] == sum( delta_sg[g,i,t] for i in gen_startup_categories[g])) # (16)

        @constraint(m, pg[g,t] + rg[g,t] <= (gen["power_output_maximum"] - gen["power_output_minimum"])*ug[g,t] - max(0, (gen["power_output_maximum"] - gen["ramp_startup_limit"]))*vg[g,t]) # (17)

        if t < data["time_periods"]
            @constraint(m, pg[g,t] + rg[g,t] <= (gen["power_output_maximum"] - gen["power_output_minimum"])*ug[g,t] - max(0, (gen["power_output_maximum"] - gen["ramp_shutdown_limit"]))*wg[g,t+1]) # (18)
        end

        @constraint(m, pg[g,t] == sum((gen["piecewise_production"][l]["mw"] - gen["piecewise_production"][1]["mw"])*lambda_lg[g,l,t] for l in gen_pwl_points[g])) # (21)
        @constraint(m, cg[g,t] == sum((gen["piecewise_production"][l]["cost"] - gen["piecewise_production"][1]["cost"])*lambda_lg[g,l,t] for l in gen_pwl_points[g])) # (22)
        @constraint(m, ug[g,t] == sum(lambda_lg[g,l,t] for l in gen_pwl_points[g])) # (23)
    end

    for (rg, rgen) in data["renewable_generators"]
        @constraint(m, rgen["power_output_minimum"][t] <= pw[rg,t] <= rgen["power_output_maximum"][t]) # (24)
    end
end


println("optimization")

using Cbc
optimize!(m, with_optimizer(Cbc.Optimizer, logLevel=1))
