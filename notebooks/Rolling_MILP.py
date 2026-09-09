import pyomo.environ as pyo
import numpy as np
from datetime import datetime, timedelta

from dataclasses import dataclass
import matplotlib.pyplot as plt


prices = np.random.default_rng(42).normal(0.5, 0.8, 96)
granularity = 15
horizon = 95
now = datetime(2026,9,8,10,0)
dt = granularity / 60

### PRICES

def price_at_time(hour, rng, previous_price=None):
    """

    Price unit: €/kWh
    """

    # -------------------------
    # Base price
    # -------------------------
    base_price = 0.075

    # -------------------------
    # Morning demand peak
    # -------------------------
    morning_peak = (
        0.045
        * np.exp(
            -0.5 * ((hour - 8) / 2.0) ** 2
        )
    )

    # -------------------------
    # Evening demand peak
    # -------------------------
    evening_peak = (
        0.060
        * np.exp(
            -0.5 * ((hour - 18) / 2.5) ** 2
        )
    )

    # -------------------------
    # Midday renewable effect
    # -------------------------
    midday_effect = (
        -0.040
        * np.exp(
            -0.5 * ((hour - 13) / 2.5) ** 2
        )
    )

    # -------------------------
    # Low nighttime demand
    # -------------------------
    night_effect = (
        -0.025
        * np.exp(
            -0.5 * ((hour - 3) / 2.5) ** 2
        )
    )

    theoretical_price = (
        base_price
        + morning_peak
        + evening_peak
        + midday_effect
        + night_effect
    )

    # -------------------------
    # Random market fluctuation
    # -------------------------
    random_component = rng.normal(0, 0.005)

    price = theoretical_price + random_component

    # -------------------------
    # Temporal correlation
    # -------------------------
    if previous_price is not None:
        price = (
            0.75 * previous_price
            + 0.25 * price
        )

    return price


def initialize_prices(
    start_hour=10,
    horizon=96,
    granularity=15,
    seed=42
):

    rng = np.random.default_rng(seed)

    dt = granularity / 60

    prices = [
        price_at_time(
            (start_hour + t * dt) % 24,
            rng
        )
        for t in range(horizon)
    ]

    return prices, rng



############ VEHICLES


@dataclass
class ElectricVehicle:
    id: int
    battery_level: float
    battery_capacity: float
    time_arrival: datetime
    time_frame_desired: float
    desired_energy_stated: float
    charge_power: float
    discharge_power: float
    battery_level_theory: float

vehicles = []


vehicles = [
     ElectricVehicle(1, 18, 60, now, 6.0, 0.9, 22, 11, 18)
     ]




############# OPTIMIZATION MODEL

def build_milp(vehicles, prices, granularity, horizon, current_time):

    model = pyo.ConcreteModel()


    ### Sets
    model.V = pyo.Set(initialize=[v.id for v in vehicles])
    model.T = pyo.RangeSet(0, horizon - 1)
    model.T_energy = pyo.RangeSet(0, horizon)


    ###DECISION VARIABLE
    model.charge = pyo.Var(
        model.V,
        model.T,
        within=pyo.NonNegativeReals
    )

    model.discharge = pyo.Var(
        model.V,
        model.T,
        within=pyo.NonNegativeReals
    )


    ### STATE VARIABLES

    # ENERGY AT EVERY STEP

    model.energy = pyo.Var(
        model.V,
        model.T_energy,
        within=pyo.NonNegativeReals
    )

    # is charging?

    model.is_charging = pyo.Var(
        model.V,
        model.T,
        within=pyo.Binary
    )

    ###OBJECTIVE FUNCTION

    model.objective = pyo.Objective(
        expr=sum(
            (
                prices[t] * (model.charge[v, t]
                - model.discharge[v, t])
            ) * granularity/60
            for v in model.V
            for t in model.T
        ),
        sense=pyo.minimize
    )


    ### CONSTRAINTS

    # CHARGE LIMIT

    def charge_limit_rule(model, v, t):
        vehicle = next(vehicle for vehicle in vehicles if vehicle.id == v)

        return model.charge[v, t] <= vehicle.charge_power

    model.charge_limit = pyo.Constraint(
        model.V,
        model.T,
        rule=charge_limit_rule
    )

    # DISCHARGE LIMIT

    def discharge_limit_rule(model, v, t):
        vehicle = next(vehicle for vehicle in vehicles if vehicle.id == v)

        return model.discharge[v, t] <= vehicle.discharge_power

    model.discharge_limit = pyo.Constraint(
        model.V,
        model.T,
        rule=discharge_limit_rule
    )

    # INITIAL

    def initial_energy_rule(model, v):
        vehicle = next(vehicle for vehicle in vehicles if vehicle.id == v)

        return model.energy[v, 0] == vehicle.battery_level

    model.initial_energy = pyo.Constraint(
        model.V,
        rule=initial_energy_rule
    )

    # ENERGY EVOLUTION

    dt = granularity / 60  # hours

    def energy_evolution_rule(model, v, t):
        return model.energy[v, t + 1] == (
            model.energy[v, t]
            + model.charge[v, t] * dt
            - model.discharge[v, t] * dt
        )

    model.energy_evolution = pyo.Constraint(
        model.V,
        model.T,
        rule=energy_evolution_rule
    )

    # AVOID CHARGING AND DISCHARGING

    def charging_status_rule(model, v, t):
        vehicle = next(vehicle for vehicle in vehicles if vehicle.id == v)

        return model.charge[v, t] <= vehicle.charge_power * model.is_charging[v, t]

    model.charging_status = pyo.Constraint(
        model.V,
        model.T,
        rule=charging_status_rule
    )

    def discharging_status_rule(model, v, t):
        vehicle = next(vehicle for vehicle in vehicles if vehicle.id == v)

        return model.discharge[v, t] <= vehicle.discharge_power * (1 - model.is_charging[v, t])

    model.discharging_status = pyo.Constraint(
        model.V,
        model.T,
        rule=discharging_status_rule
    )

    # ENERGY SHOULD ALWAYS BE OVER 20% (EXCEPT WHEN IT STARTED CHARGING BELOW)

    def minimum_energy_rule(model, v, t):
        vehicle = next(vehicle for vehicle in vehicles if vehicle.id == v)

        E0 = vehicle.battery_level
        E_min = 0.2 * vehicle.battery_capacity

        required_energy = min(
            E_min,
            E0 + vehicle.charge_power * t * dt
        )

        return model.energy[v, t] >= required_energy

    model.minimum_energy = pyo.Constraint(
        model.V,
        model.T_energy,
        rule=minimum_energy_rule
    )


    # ENERGY SHOULD REACH THE ENERGY WISHED AT THE TIME STATED IF POSSIBLE (OTHERWISE CHARGE AS MUCH AS POSSIBLE)

    def departure_energy_rule(model, v):
        vehicle = next(vehicle for vehicle in vehicles if vehicle.id == v)

        E0 = vehicle.battery_level
        E_target = vehicle.desired_energy_stated * vehicle.battery_capacity

        time_available = max(0,vehicle.time_frame_desired - (current_time-vehicle.time_arrival).total_seconds()/3600)

        E_max_possible = (
            E0 + vehicle.charge_power * time_available
        )

        E_required = min(E_target, E_max_possible)

        departure_t = int(time_available / dt)

        return model.energy[v, departure_t] >= E_required

    model.departure_energy = pyo.Constraint(
        model.V,
        rule=departure_energy_rule
    )

    # ENERGY IS BOUNDED

    def capacity_rule(model, v, t):
        vehicle = next(vehicle for vehicle in vehicles if vehicle.id == v)

        return model.energy[v, t] <= vehicle.battery_capacity

    model.capacity = pyo.Constraint(
        model.V,
        model.T_energy,
        rule=capacity_rule
    )


    # CHARGING MUST BE ZERO AFTER DEPARTURE
    def unplugged_charge_rule(model, v, t):
        vehicle = next(vehicle for vehicle in vehicles if vehicle.id == v)

        time_available = max(0,vehicle.time_frame_desired - (current_time-vehicle.time_arrival).total_seconds()/3600)

        departure_t = int(time_available / dt)

        if t >= departure_t:
            return model.charge[v, t] == 0

        return pyo.Constraint.Skip

    model.unplugged_charge = pyo.Constraint(
        model.V,
        model.T,
        rule=unplugged_charge_rule
    )


    # DISCHARGING MUST BE ZERO AFTER DEPARTURE
    def unplugged_discharge_rule(model, v, t):
        vehicle = next(vehicle for vehicle in vehicles if vehicle.id == v)

        time_available = max(0,vehicle.time_frame_desired - (current_time-vehicle.time_arrival).total_seconds()/3600)
        departure_t = int(time_available / dt)

        if t >= departure_t:
            return model.discharge[v, t] == 0

        return pyo.Constraint.Skip

    model.unplugged_discharge = pyo.Constraint(
        model.V,
        model.T,
        rule=unplugged_discharge_rule
    )

    return model


#################################

current_time = now

prices, rng = initialize_prices(
    start_hour=10,
    horizon=96,
    granularity=15,
    seed=42
)


model = build_milp(vehicles, prices, granularity, horizon, current_time)

solver = pyo.SolverFactory("highs")

results = solver.solve(model, tee=True)


#### RESULTS:


print("Minimized cost:", pyo.value(model.objective))

dt=granularity/60
#
# for v in vehicles:
#     departure_t = int(v.time_frame_desired / dt)
#
#     print(f"\nVehicle {v.id}")
#
#     for t in range(departure_t + 1):
#         charge = pyo.value(model.charge[v.id, t])
#         discharge = pyo.value(model.discharge[v.id, t])
#         energy = pyo.value(model.energy[v.id, t])
#
#         print(
#             f"t={t:2d} | "
#             f"energy={energy:6.2f} kWh | "
#             f"charge={charge:5.2f} kW | "
#             f"discharge={discharge:5.2f} kW"
#         )


### VISUALIZE

# dt = granularity / 60
#
# for v in vehicles:
#     # Departure timestep
#     departure_t = int(v.time_frame_desired / dt)
#
#     # -------------------------
#     # Energy data
#     # -------------------------
#     times_energy = [
#         t * dt
#         for t in range(departure_t + 1)
#     ]
#
#     energy = [
#         pyo.value(model.energy[v.id, t])
#         for t in range(departure_t + 1)
#     ]
#
#     # -------------------------
#     # Price data
#     # -------------------------
#     times_price = [
#         t * dt
#         for t in range(departure_t)
#     ]
#
#     vehicle_prices = prices[:departure_t]
#
#     # -------------------------
#     # Create figure
#     # -------------------------
#     fig, ax1 = plt.subplots(figsize=(10, 5))
#
#     # Battery energy
#     ax1.plot(
#         times_energy,
#         energy,
#         marker="o",
#         label="Battery energy"
#     )
#
#     # Desired energy
#     target_energy = (
#         v.desired_energy_stated
#         * v.battery_capacity
#     )
#
#     ax1.axhline(
#         target_energy,
#         linestyle="--",
#         label="Desired energy"
#     )
#
#     # 20% minimum
#     minimum_energy = 0.2 * v.battery_capacity
#
#     ax1.axhline(
#         minimum_energy,
#         linestyle=":",
#         label="20% minimum"
#     )
#
#     # Battery capacity
#     ax1.axhline(
#         v.battery_capacity,
#         color="red",
#         linestyle="-",
#         label="Battery capacity"
#     )
#
#     # -------------------------
#     # Left axis
#     # -------------------------
#     ax1.set_xlabel("Time (hours)")
#     ax1.set_ylabel("Energy (kWh)")
#
#     ax1.set_ylim(
#         0,
#         v.battery_capacity * 1.05
#     )
#
#     ax1.grid(True)
#
#     # -------------------------
#     # Right axis: price
#     # -------------------------
#     ax2 = ax1.twinx()
#
#     ax2.step(
#         times_price,
#         vehicle_prices,
#         where="post",
#         alpha=0.5,
#         label="Market price"
#     )
#
#     ax2.set_ylabel("Market price (€/MWh)")
#
#     # -------------------------
#     # Combined legend
#     # -------------------------
#     lines1, labels1 = ax1.get_legend_handles_labels()
#     lines2, labels2 = ax2.get_legend_handles_labels()
#
#     ax1.legend(
#         lines1 + lines2,
#         labels1 + labels2,
#         loc="best"
#     )
#
#     # -------------------------
#     # Title
#     # -------------------------
#     plt.title(
#         f"Vehicle {v.id} – Energy and Market Price"
#     )
#
#     plt.tight_layout()
#     if v.id == 2:
#         plt.show()



##### ROLLING

def update_prices(
    prices,
    current_time,
    granularity,
    rng
):


    dt = granularity / 60

    # Remove the price that has just passed
    prices.pop(0)

    # Generate the new price at the end of the horizon
    new_time = current_time + timedelta(minutes = granularity)

    new_price = price_at_time(
        current_time.hour,
        rng
    )

    prices.append(new_price)

    return prices,rng



car_profiles = [
        {"capacity": 35.0, "max_charge": 7.4,  "max_discharge": 0.0},   # small EV, AC-only
        {"capacity": 60.0, "max_charge": 11.0, "max_discharge": 7.0},   # mid-size, V2G-capable
        {"capacity": 85.0, "max_charge": 22.0, "max_discharge": 10.0},  # large EV
        {"capacity": 42.0, "max_charge": 8,  "max_discharge": 0.0},   # small EV, AC-only
        {"capacity": 65.0, "max_charge": 10.0, "max_discharge": 6.0},   # mid-size, V2G-capable
        {"capacity": 90.0, "max_charge": 30.0, "max_discharge": 15.0},  # large EV
    ]


def generate_parking_time(current_time, rng):
    if 6 <= current_time.hour < 10:
        # Morning → workday
        parking_time = rng.normal(8, 1.5)
    elif 10 <= current_time.hour  < 16:
        # Midday → shorter stay
        parking_time = rng.normal(4, 1.5)
    elif 16 <= current_time.hour  < 21:
        # Evening → overnight
        parking_time = rng.normal(14, 2)
    else:
        # Night
        parking_time = rng.normal(7, 2)
    return max(round(parking_time/(granularity/60))*0.25, 0.25)

def sample_vehicle(last_id,rng):
    id = last_id + 1
    profile = np.random.choice(car_profiles)
    battery_capacity = profile["capacity"]
    battery_level = round(np.random.uniform(0.1,0.6),2)*battery_capacity
    time_frame_desired = generate_parking_time(current_time,rng)
    charge_power = profile["max_charge"]
    discharge_power = profile["max_discharge"]
    battery_level_desired = 0.8 if np.random.random()>0.5 else 1
    battery_level_theory = battery_level

    return ElectricVehicle(id, battery_level, battery_capacity, current_time, time_frame_desired, battery_level_desired, charge_power, discharge_power, battery_level_theory)



def number_of_arrivals(hour, rng):
    if 7 <= hour < 10:       # morning peak
        rate = 15
    elif 10 <= hour < 16:    # midday
        rate = 10
    elif 16 <= hour < 20:    # afternoon peak
        rate = 15
    else:                    # night
        rate = 2
    return rng.poisson(rate * 0.25)

current_time = now
drop_rate = 0.02
max_vehicles = 100
last_id = len(vehicles)

real_cost=[]
theory_cost=[]

for i in range(48):
    real_cost.append(0)
    theory_cost.append(0)
    current_time = current_time + timedelta(minutes = 15)

    for v in vehicles:
        if v.time_arrival + timedelta(hours = v.time_frame_desired) < current_time:
            vehicles.remove(v)
        if np.random.random() > (1-drop_rate):
            vehicles.remove(v)
        else:
            v.battery_level += (
                pyo.value(model.charge[v.id, 0]) - pyo.value(model.discharge[v.id, 0])) * dt
            real_cost[i]+=(pyo.value(model.charge[v.id, 0]) - pyo.value(model.discharge[v.id, 0])) * dt * prices[0]
            if v.battery_level_theory + v.charge_power * dt < v.battery_capacity:
                v.battery_level_theory += v.charge_power * dt
                theory_cost[i]+=v.charge_power * dt * prices[0]
            else:
                theory_cost[i] += (v.battery_capacity - v.battery_level_theory)*prices[0]
                v.battery_level_theory = v.battery_capacity



    prices,rng = update_prices(prices, current_time, granularity, rng)
    number_of_vehicle_to_sample = number_of_arrivals(current_time.hour,rng)
    for i in range(number_of_vehicle_to_sample):
        if len(vehicles) < max_vehicles:
            new_vehicle = sample_vehicle(last_id,rng)
            last_id = last_id + 1
        vehicles.append(new_vehicle)

    model = build_milp(vehicles, prices, granularity, horizon, current_time)
    solver = pyo.SolverFactory("highs")
    results = solver.solve(model, tee=True)


### VISUALIZE

dt = granularity / 60

#Arbitrary
vehicle_to_check = 6

if len(vehicles)>vehicle_to_check:
    v=vehicles[vehicle_to_check-1]

    # Departure timestep
    time_available = max(0,v.time_frame_desired - (current_time-v.time_arrival).total_seconds()/3600)
    departure_t = int(time_available / dt)

    # -------------------------
    # Energy data
    # -------------------------
    times_energy = [
        t * dt
        for t in range(departure_t + 1)
    ]

    energy = [
        pyo.value(model.energy[v.id, t])
        for t in range(departure_t + 1)
    ]

    # -------------------------
    # Price data
    # -------------------------
    times_price = [
        t * dt
        for t in range(departure_t)
    ]

    vehicle_prices = prices[:departure_t]

    # -------------------------
    # Create figure
    # -------------------------
    fig, ax1 = plt.subplots(figsize=(10, 5))

    # Battery energy
    ax1.plot(
        times_energy,
        energy,
        marker="o",
        label="Battery energy"
    )

    # Desired energy
    target_energy = (
        v.desired_energy_stated
        * v.battery_capacity
    )

    ax1.axhline(
        target_energy,
        linestyle="--",
        label="Desired energy"
    )

    # 20% minimum
    minimum_energy = 0.2 * v.battery_capacity

    ax1.axhline(
        minimum_energy,
        linestyle=":",
        label="20% minimum"
    )

    # Battery capacity
    ax1.axhline(
        v.battery_capacity,
        color="red",
        linestyle="-",
        label="Battery capacity"
    )

    # -------------------------
    # Left axis
    # -------------------------
    ax1.set_xlabel("Time (hours)")
    ax1.set_ylabel("Energy (kWh)")

    ax1.set_ylim(
        0,
        v.battery_capacity * 1.05
    )

    ax1.grid(True)

    # -------------------------
    # Right axis: price
    # -------------------------
    ax2 = ax1.twinx()

    ax2.step(
        times_price,
        vehicle_prices,
        where="post",
        alpha=0.5,
        label="Market price"
    )

    ax2.set_ylabel("Market price (€/MWh)")

    # -------------------------
    # Combined legend
    # -------------------------
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()

    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="best"
    )

    # -------------------------
    # Title
    # -------------------------
    plt.title(
        f"Vehicle {v.id} – Energy and Market Price"
    )

    plt.tight_layout()
    plt.show()