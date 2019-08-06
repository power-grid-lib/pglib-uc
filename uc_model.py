from pyomo.environ import *
import json
import sys

## Grab instance file from first command line argument
data_file = sys.argv[1]

print('loading data')
data = json.load(open(data_file, 'r'))

thermal_gens = data['thermal_generators']
renewable_gens = data['renewable_generators']

time_periods = {t+1 : t for t in range(data['time_periods'])}

gen_startup_categories = {g : list(range(0, len(gen['startup']))) for (g, gen) in thermal_gens.items()}
gen_pwl_points = {g : list(range(0, len(gen['piecewise_production']))) for (g, gen) in thermal_gens.items()}

print('building model')
m = ConcreteModel()

m.cg = Var(thermal_gens.keys(), time_periods.keys())
m.pg = Var(thermal_gens.keys(), time_periods.keys(), within=NonNegativeReals)  
m.rg = Var(thermal_gens.keys(), time_periods.keys(), within=NonNegativeReals)  
m.pw = Var(renewable_gens.keys(), time_periods.keys(), within=NonNegativeReals)
m.ug = Var(thermal_gens.keys(), time_periods.keys(), within=Binary) 
m.vg = Var(thermal_gens.keys(), time_periods.keys(), within=Binary) 
m.wg = Var(thermal_gens.keys(), time_periods.keys(), within=Binary) 

m.dg = Var(((g,s,t) for g in thermal_gens for s in gen_startup_categories[g] for t in time_periods), within=Binary) ##
m.lg = Var(((g,l,t) for g in thermal_gens for l in gen_pwl_points[g] for t in time_periods), within=UnitInterval) ##

m.obj = Objective(expr=sum(
                          sum(
                              m.cg[g,t] + gen['piecewise_production'][0]['cost']*m.ug[g,t]
                              + sum( gen_startup['cost']*m.dg[g,s,t] for (s, gen_startup) in enumerate(gen['startup']))
                          for t in time_periods)
                        for g, gen in thermal_gens.items() )
                        ) #(1)

m.demand = Constraint(time_periods.keys())
m.reserves = Constraint(time_periods.keys())
for t,t_idx in time_periods.items():
    m.demand[t] = sum( m.pg[g,t]+gen['power_output_minimum']*m.ug[g,t] for (g, gen) in thermal_gens.items() ) + sum( m.pw[w,t] for w in renewable_gens ) == data['demand'][t_idx] #(2)
    m.reserves[t] = sum( m.rg[g,t] for g in thermal_gens ) >= data['reserves'][t_idx] #(3)

m.uptimet0 = Constraint(thermal_gens.keys())
m.downtimet0 = Constraint(thermal_gens.keys())
m.logicalt0 = Constraint(thermal_gens.keys())
m.startupt0 = Constraint(thermal_gens.keys())

m.rampupt0 = Constraint(thermal_gens.keys())
m.rampdownt0 = Constraint(thermal_gens.keys())
m.shutdownt0 = Constraint(thermal_gens.keys())

for g, gen in thermal_gens.items():
    if gen['unit_on_t0'] == 1:
        if gen['time_up_minimum'] - gen['time_up_t0'] >= 1:
            m.uptimet0[g] = sum( (m.ug[g,t] - 1) for t in range(1, min(gen['time_up_minimum'] - gen['time_up_t0'], data['time_periods'])+1)) == 0 #(4)
    elif gen['unit_on_t0'] == 0:
        if gen['time_down_minimum'] - gen['time_down_t0'] >= 1:
            m.downtimet0[g] = sum( m.ug[g,t] for t in range(1, min(gen['time_down_minimum'] - gen['time_down_t0'], data['time_periods'])+1)) == 0 #(5)
    else:
        raise Exception('Invalid unit_on_t0 for generator {}, unit_on_t0={}'.format(g, gen['unit_on_t0']))

    m.logicalt0[g] = m.ug[g,1] - gen['unit_on_t0'] == m.vg[g,1] - m.wg[g,1] #(6)

    startup_expr = sum( 
                        sum( m.dg[g,s,t] 
                                for t in range(
                                                max(1,gen['startup'][s+1]['lag']-gen['time_down_t0']+1),
                                                min(gen['startup'][s+1]['lag']-1,data['time_periods'])+1
                                              )
                            ) 
                       for s,_ in enumerate(gen['startup'][:-1])) ## all but last
    if isinstance(startup_expr, int):
        pass
    else:
        m.startupt0[g] = startup_expr == 0 #(7)

    m.rampupt0[g] = m.pg[g,1] + m.rg[g,1] - gen['unit_on_t0']*(gen['power_output_t0']-gen['power_output_minimum']) <= gen['ramp_up_limit'] #(8)

    m.rampdownt0[g] = gen['unit_on_t0']*(gen['power_output_t0']-gen['power_output_minimum']) - m.pg[g,1] <= gen['ramp_down_limit'] #(9)


    shutdown_constr = gen['unit_on_t0']*(gen['power_output_t0']-gen['power_output_minimum']) <= gen['unit_on_t0']*(gen['power_output_maximum'] - gen['power_output_minimum']) - max((gen['power_output_maximum'] - gen['ramp_shutdown_limit']),0)*m.wg[g,1] #(10)

    if isinstance(shutdown_constr, bool):
        pass
    else:
        m.shutdownt0[g] = shutdown_constr

m.mustrun = Constraint(thermal_gens.keys(), time_periods.keys())
m.logical = Constraint(thermal_gens.keys(), time_periods.keys())
m.uptime = Constraint(thermal_gens.keys(), time_periods.keys())
m.downtime = Constraint(thermal_gens.keys(), time_periods.keys())
m.startup_select = Constraint(thermal_gens.keys(), time_periods.keys())
m.gen_limit1 = Constraint(thermal_gens.keys(), time_periods.keys())
m.gen_limit2 = Constraint(thermal_gens.keys(), time_periods.keys())
m.ramp_up = Constraint(thermal_gens.keys(), time_periods.keys())
m.ramp_down = Constraint(thermal_gens.keys(), time_periods.keys())
m.power_select = Constraint(thermal_gens.keys(), time_periods.keys())
m.cost_select = Constraint(thermal_gens.keys(), time_periods.keys())
m.on_select = Constraint(thermal_gens.keys(), time_periods.keys())

for g, gen in thermal_gens.items():
    for t in time_periods:
        m.mustrun[g,t] = m.ug[g,t] >= gen['must_run'] #(11)

        if t > 1:
            m.logical[g,t] = m.ug[g,t] - m.ug[g,t-1] == m.vg[g,t] - m.wg[g,t] #(12)

        UT = min(gen['time_up_minimum'],data['time_periods'])
        if t >= UT:
            m.uptime[g,t] = sum(m.vg[g,t] for t in range(t-UT+1, t+1)) <= m.ug[g,t] #(13)
        DT = min(gen['time_down_minimum'],data['time_periods'])
        if t >= DT:
            m.downtime[g,t] = sum(m.wg[g,t] for t in range(t-DT+1, t+1)) <= 1-m.ug[g,t] #(14)
        m.startup_select[g,t] = m.vg[g,t] == sum(m.dg[g,s,t] for s,_ in enumerate(gen['startup'])) #(16)

        m.gen_limit1[g,t] = m.pg[g,t]+m.rg[g,t] <= (gen['power_output_maximum'] - gen['power_output_minimum'])*m.ug[g,t] - max((gen['power_output_maximum'] - gen['ramp_startup_limit']),0)*m.vg[g,t] #(17)

        if t < len(time_periods): 
            m.gen_limit2[g,t] = m.pg[g,t]+m.rg[g,t] <= (gen['power_output_maximum'] - gen['power_output_minimum'])*m.ug[g,t] - max((gen['power_output_maximum'] - gen['ramp_shutdown_limit']),0)*m.wg[g,t+1] #(18)

        if t > 1:
            m.ramp_up[g,t] = m.pg[g,t]+m.rg[g,t] - m.pg[g,t-1] <= gen['ramp_up_limit'] #(19)
            m.ramp_down[g,t] = m.pg[g,t-1] - m.pg[g,t] <= gen['ramp_down_limit'] #(20

        piece_mw1 = gen['piecewise_production'][0]['mw']
        piece_cost1 = gen['piecewise_production'][0]['cost']
        m.power_select[g,t] = m.pg[g,t] == sum( (piece['mw'] - piece_mw1)*m.lg[g,l,t] for l,piece in enumerate(gen['piecewise_production'])) #(21)
        m.cost_select[g,t] = m.cg[g,t] == sum( (piece['cost'] - piece_cost1)*m.lg[g,l,t] for l,piece in enumerate(gen['piecewise_production'])) #(22)
        m.on_select[g,t] = m.ug[g,t] == sum(m.lg[g,l,t] for l,_ in enumerate(gen['piecewise_production'])) #(23)

m.startup_allowed = Constraint(m.dg_index)
for g, gen in thermal_gens.items():
    for s,_ in enumerate(gen['startup'][:-1]): ## all but last
        for t in time_periods:
            if t >= gen['startup'][s+1]['lag']:
                m.startup_allowed[g,s,t] = m.dg[g,s,t] <= sum(m.wg[g,t-i] for i in range(gen['startup'][s]['lag'], gen['startup'][s+1]['lag'])) #(15)

for w, gen in renewable_gens.items():
    for t, t_idx in time_periods.items():
        m.pw[w,t].setlb(gen['power_output_minimum'][t_idx]) #(24)
        m.pw[w,t].setub(gen['power_output_maximum'][t_idx]) #(24)

print("model setup complete")

from pyomo.opt import SolverFactory
cbc = SolverFactory('cbc')

print("solving")
cbc.solve(m, options={'ratioGap':0.01}, tee=True)
