import math
from copy import deepcopy
from dataclasses import dataclass, field, replace
from enum import Enum
from pprint import pprint
from typing import ClassVar, Dict, List, Optional, Self, Tuple

import gravis as gv

ALLOW_QUALITY = True
ALLOW_RECYCLING = True


@dataclass
class Machine:
    name: str
    speed: float = 1
    module_slots: int = 0
    preferred_beacons: int = 0
    base_prod: float = 1


@dataclass(frozen=True, order=True, init=False)
class Item:
    name: str
    quality: int = 1
    is_fluid: bool = False

    MIN_QUALITY: ClassVar[int] = 1
    MAX_QUALITY: ClassVar[int] = 5

    QUALITY_SUFFIX: ClassVar[Dict[int, str]] = {
        1: "‧",
        2: "⁚",
        3: "⁖",
        4: "⁘",
        5: "⁙",
    }

    def __init__(self, name: str, quality: int = MIN_QUALITY, is_fluid: bool = False):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "quality", quality if not is_fluid else Item.MIN_QUALITY)
        object.__setattr__(self, "is_fluid", is_fluid)

    def __repr__(self):
        if self.is_fluid:
            return f"{self.name}"
        else:
            return f"{self.name} q{self.quality}"

    def __str__(self):
        if self.is_fluid:
            return f"{self.name}"
        elif ALLOW_QUALITY:
            return f"{self.name} {Item.QUALITY_SUFFIX[self.quality]}"
        else:
            return f"{self.name}"


def Fluid(name: str) -> Item:
    return Item(name, is_fluid=True)


@dataclass
class Bonus:
    name: str
    speed: float = 0
    prod: float = 0
    quality: float = 0

    def __add__(self, other: Self) -> Self:
        return Bonus(
            name="", speed=self.speed + other.speed, prod=self.prod + other.prod, quality=self.quality + other.quality
        )

    def __mul__(self, scale: float) -> Self:
        return Bonus(self.name, speed=self.speed * scale, prod=self.prod * scale, quality=self.quality * scale)

    def __rmul__(self, scale: float) -> Self:
        return self.__mul__(scale)


ZERO_BONUS = Bonus(name="zero")

ItemCounts = Dict[Item, float]


@dataclass
class Recipe:
    name: str
    time: float
    machine: str
    inputs: ItemCounts
    outputs: ItemCounts
    quality: int = Item.MIN_QUALITY
    applicable_bonuses: List[str] = field(default_factory=list)
    can_prod: bool = True
    recyclable: bool = True


@dataclass
class Beacon:
    name: str
    transmission: float
    effect: Bonus


@dataclass
class MachineSettings:
    name: str
    module: Bonus  # only one type of module per machine
    is_prod: bool
    num_beacons: Optional[int] = 0  # None implies using the machine's preferred
    beacon: Optional[Beacon] = None

    def effect_total(self, machine: Machine) -> Bonus:
        effect = self.module * machine.module_slots
        num_beacons = self.num_beacons if self.num_beacons is not None else machine.preferred_beacons
        if self.beacon and num_beacons:
            effect += (self.beacon.transmission * (num_beacons**0.5)) * self.beacon.effect
        if effect.speed < -0.8:
            effect.speed = -0.8
        return effect


@dataclass
class Configuration:
    name: str
    machines: List[Machine]
    recipes: List[Recipe]
    global_bonuses: List[Bonus]
    machine_settings_available: List[MachineSettings]


BASE_RESOURCE = Item("resource", is_fluid=True)


def MakeDefaultConfiguration() -> Configuration:

    speed_module = Bonus(name="speed_3", speed=0.5, quality=-0.15)
    prod_module = Bonus(name="prod_3", prod=0.1, speed=-0.15)
    quality_module = Bonus(name="quality_3", quality=0.025, speed=-0.05)
    # quality_module = Bonus(name="quality_3", quality=0.025 * 2.5, speed=-0.05)
    config = Configuration(
        name="default",
        machines=[
            Machine(name="big_miner", speed=2.5, module_slots=4, preferred_beacons=0),
            Machine(name="offshore_pump", speed=1, module_slots=0, preferred_beacons=0),
            Machine(name="pumpjack", speed=1, module_slots=2, preferred_beacons=0),
            Machine(name="cryo_plant", speed=2, module_slots=8, preferred_beacons=8),
            Machine(name="oil_refinery", speed=1, module_slots=3, preferred_beacons=8),
            Machine(name="electro_plant", speed=2, base_prod=1.5, module_slots=5, preferred_beacons=8),
            Machine(name="chem_plant", speed=1, module_slots=3, preferred_beacons=8),
            Machine(name="assembler_3", speed=1.25, module_slots=4, preferred_beacons=8),
            Machine(name="furnace", speed=2, module_slots=2, preferred_beacons=8),
            Machine(name="foundry", speed=4, module_slots=4, preferred_beacons=8, base_prod=1.5),
            Machine(name="recycler", speed=0.5, module_slots=4, preferred_beacons=8),
        ],
        recipes=[
            Recipe(
                name="pump_water",
                time=1,
                machine="offshore_pump",
                inputs={},
                outputs={Fluid("water"): 1200},
                recyclable=False,
            ),
            Recipe(
                name="mine_copper",
                time=1,
                machine="big_miner",
                inputs={BASE_RESOURCE: 1},
                outputs={Item("copper"): 1},
                applicable_bonuses=["mining_productivity"],
                recyclable=False,
            ),
            Recipe(
                name="mine_iron",
                time=1,
                machine="big_miner",
                inputs={BASE_RESOURCE: 1},
                outputs={Item("iron"): 1},
                applicable_bonuses=["mining_productivity"],
                recyclable=False,
            ),
            Recipe(
                name="mine_coal",
                time=1,
                machine="big_miner",
                inputs={BASE_RESOURCE: 1},
                outputs={Item("coal"): 1},
                applicable_bonuses=["mining_productivity"],
                recyclable=False,
            ),
            Recipe(
                name="mine_stone",
                time=1,
                machine="big_miner",
                inputs={BASE_RESOURCE: 1},
                outputs={Item("stone"): 1},
                applicable_bonuses=["mining_productivity"],
                recyclable=False,
            ),
            Recipe(
                "mine_scrap",
                time=0.5,
                machine="big_miner",
                inputs={BASE_RESOURCE: 1},
                outputs={Item("scrap"): 1},
                applicable_bonuses=["mining_productivity"],
                recyclable=False,
            ),
            Recipe(
                "crude_oil",
                time=1,
                machine="pumpjack",
                inputs={BASE_RESOURCE: 1},
                outputs={Fluid("crude_oil"): 10},
                applicable_bonuses=["mining_productivity"],
                recyclable=False,
            ),
            Recipe(
                name="copper_plate",
                time=3.2,
                machine="furnace",
                inputs={Item("copper"): 1},
                outputs={Item("copper_plate"): 1},
                recyclable=False,
            ),
            Recipe(
                name="iron_plate",
                time=3.2,
                machine="furnace",
                inputs={Item("iron"): 1},
                outputs={Item("iron_plate"): 1},
                recyclable=False,
            ),
            Recipe(
                name="holmium_solution",
                time=1,
                machine="chem_plant",
                inputs={Item("holmium"): 2, Fluid("water"): 10, Item("stone"): 1},
                outputs={Fluid("holmium_solution"): 100},
                recyclable=False,
            ),
            Recipe(
                name="holmium_plate",
                time=1,
                machine="foundry",
                inputs={Fluid("holmium_solution"): 20},
                outputs={Item("holmium_plate"): 1},
                recyclable=False,
            ),
            Recipe(
                name="steel_plate",
                time=16,
                machine="furnace",
                inputs={Item("iron_plate"): 5},
                outputs={Item("steel_plate"): 1},
                applicable_bonuses=["steel_productivity"],
                recyclable=False,
            ),
            Recipe(
                name="oil_processing",
                time=5,
                machine="oil_refinery",
                inputs={Fluid("crude_oil"): 100},
                outputs={Fluid("petro"): 45},
                recyclable=False,
            ),
            Recipe(
                name="advanced_oil_processing",
                time=5,
                machine="oil_refinery",
                inputs={Fluid("crude_oil"): 100, Fluid("water"): 50},
                outputs={Fluid("heavy_oil"): 25, Fluid("light_oil"): 45, Fluid("petro"): 55},
                recyclable=False,
            ),
            Recipe(
                name="plastic",
                time=1,
                machine="cryo_plant",
                inputs={Fluid("petro"): 20, Item("coal"): 1},
                outputs={Item("plastic"): 2},
                applicable_bonuses=["plastic_productivity"],
                recyclable=False,
            ),
            Recipe(
                name="sulfur",
                time=1,
                machine="cryo_plant",
                inputs={Fluid("water"): 30, Fluid("petro"): 30},
                outputs={Item("sulfur"): 2},
                recyclable=False,
            ),
            Recipe(
                name="sulfuric_acid",
                time=1,
                machine="cryo_plant",
                inputs={Fluid("water"): 100, Item("iron_plate"): 1, Item("sulfur"): 5},
                outputs={Fluid("sulfuric_acid"): 50},
                recyclable=False,
            ),
            Recipe(
                name="copper_cable",
                time=0.5,
                machine="electro_plant",
                inputs={Item("copper_plate"): 1},
                outputs={Item("copper_cable"): 2},
            ),
            Recipe(
                name="superconductor",
                time=5,
                machine="electro_plant",
                inputs={Item("copper_plate"): 1, Item("plastic"): 1, Item("holmium_plate"): 1, Fluid("light_oil"): 5},
                outputs={Item("superconductor"): 2},
            ),
            Recipe(
                name="circuit",
                time=0.5,
                machine="electro_plant",
                inputs={Item("copper_cable"): 3, Item("iron_plate"): 1},
                outputs={Item("circuit"): 1},
            ),
            Recipe(
                name="advanced_circuit",
                time=6,
                machine="electro_plant",
                inputs={Item("copper_cable"): 4, Item("plastic"): 2, Item("circuit"): 2},
                outputs={Item("advanced_circuit"): 1},
            ),
            Recipe(
                name="processor",
                time=10,
                machine="electro_plant",
                inputs={Item("circuit"): 20, Item("advanced_circuit"): 2, Fluid("sulfuric_acid"): 5},
                outputs={Item("processor"): 1},
                applicable_bonuses=["processor_productivity"],
            ),
            Recipe(
                "iron_chest",
                time=0.5,
                machine="assembler_3",
                inputs={Item("iron_plate"): 8},
                outputs={Item("iron_chest"): 1},
                can_prod=False,
            ),
            Recipe(
                "steel_chest",
                time=0.5,
                machine="assembler_3",
                inputs={Item("steel_plate"): 8},
                outputs={Item("steel_chest"): 1},
                can_prod=False,
            ),
            Recipe(
                "quality_module_1",
                time=15,
                machine="electro_plant",
                inputs={Item("circuit"): 5, Item("advanced_circuit"): 5},
                outputs={Item("quality_module_1"): 1},
                can_prod=False,
            ),
            Recipe(
                "quality_module_2",
                time=30,
                machine="electro_plant",
                inputs={Item("processor"): 5, Item("advanced_circuit"): 5, Item("quality_module_1"): 4},
                outputs={Item("quality_module_2"): 1},
                can_prod=False,
            ),
            Recipe(
                "quality_module_3",
                time=30,
                machine="electro_plant",
                inputs={
                    Item("processor"): 5,
                    Item("advanced_circuit"): 5,
                    Item("quality_module_2"): 4,
                    Item("superconductor"): 1,
                },
                outputs={Item("quality_module_3"): 1},
                can_prod=False,
            ),
            Recipe(
                "scrap_recycling",
                time=0.2,
                machine="recycler",
                inputs={Item("scrap"): 1},
                outputs={
                    Item("processor"): 0.02,
                    Item("advanced_circuit"): 0.03,
                    Item("lds"): 0.01,
                    Item("solid_fuel"): 0.07,
                    Item("steel_plate"): 0.04,
                    Item("concrete"): 0.06,
                    Item("battery"): 0.04,
                    Item("ice"): 0.05,
                    Item("stone"): 0.04,
                    Item("holmium"): 0.01,
                    Item("iron_gear"): 0.2,
                    Item("copper_cable"): 0.03,
                },
                applicable_bonuses=["scrap_productivity"],
                can_prod=False,
            ),
        ],
        global_bonuses=[
            15 * Bonus(name="mining_productivity", prod=0.1),
            4 * Bonus(name="scrap_productivity", prod=0.1),
            4 * Bonus(name="steel_productivity", prod=0.1),
            7 * Bonus(name="processor_productivity", prod=0.1),
            7 * Bonus(name="plastic_productivity", prod=0.1),
        ],
        machine_settings_available=[
            # MachineSettings(
            #     name="empty",
            #     num_beacons=0,
            #     is_prod=False,
            #     module=ZERO_BONUS,
            # ),
            # MachineSettings(
            #     name="prod",
            #     num_beacons=0,
            #     module=prod_module,
            #     is_prod=True,
            # ),
            # MachineSettings(
            #     name="speed",
            #     num_beacons=0,
            #     module=speed_module,
            #     is_prod=False,
            # ),
            MachineSettings(
                name="quality",
                num_beacons=0,
                module=quality_module,
                is_prod=False,
            ),
            MachineSettings(
                name="full_balanced",
                num_beacons=None,
                beacon=Beacon(name="speed", transmission=1.5, effect=2 * speed_module),
                module=prod_module,
                is_prod=True,
            ),
            MachineSettings(
                name="full_speed",
                num_beacons=None,
                beacon=Beacon(name="speed", transmission=1.5, effect=2 * speed_module),
                module=speed_module,
                is_prod=False,
            ),
        ],
    )

    return config


BonusMap = Dict[str, Bonus]


class Transformation:

    def __init__(
        self,
        name: str,
        recipe: Recipe,
        machine: Machine,
        machine_settings: MachineSettings,
        global_bonuses: BonusMap,
    ):
        self.name = name
        self.recipe = recipe
        self.machine_settings = machine_settings

        extra_effects = machine_settings.effect_total(machine)
        for applicable_bonus in recipe.applicable_bonuses:
            extra_effects += global_bonuses.get(applicable_bonus, ZERO_BONUS)

        effective_prod = machine.base_prod + extra_effects.prod
        rate = machine.speed * (1 + extra_effects.speed) / recipe.time

        self.inputs_per_sec: ItemCounts = {}
        for item, count in recipe.inputs.items():
            net_in = count - recipe.outputs.get(item, 0)
            if net_in <= 0:
                continue
            self.inputs_per_sec[item] = net_in * rate

        zero_quality_output_rate: ItemCounts = {}
        for item, count in recipe.outputs.items():
            net_out = count - recipe.inputs.get(item, 0)
            if net_out <= 0:
                continue
            zero_quality_output_rate[item] = net_out * rate * effective_prod

        quality = extra_effects.quality
        if quality < 0:
            quality = 0
        self.outputs_per_sec: ItemCounts = {
            Item(i.name, recipe.quality): rate * (1 - quality)
            for (i, rate) in zero_quality_output_rate.items()
            if not i.is_fluid
        }
        self.outputs_per_sec.update(
            {Fluid(i.name): rate for (i, rate) in zero_quality_output_rate.items() if i.is_fluid}
        )

        if quality:
            left_over = quality
            curr_multi = quality * 0.9
            curr_quality = recipe.quality + 1
            while curr_quality <= Item.MAX_QUALITY:
                if curr_quality == Item.MAX_QUALITY:
                    curr_multi = left_over

                self.outputs_per_sec.update(
                    {
                        Item(i.name, curr_quality): rate * curr_multi
                        for (i, rate) in zero_quality_output_rate.items()
                        if not i.is_fluid
                    }
                )
                left_over -= curr_multi
                curr_quality += 1
                curr_multi *= 0.1

    def __repr__(self) -> str:
        return f"{self.name}"


def generate_recycling_recipes(recipes: List[Recipe]):
    result_recipes = [r for r in recipes]
    for recipe in recipes:
        if recipe.name.startswith("scrap"):
            continue

        if not recipe.recyclable:
            outputs = {i: c * 0.25 for (i, c) in recipe.outputs.items() if not i.is_fluid}
            if not outputs:
                continue
            assert len(outputs) == 1
            inputs = deepcopy(recipe.outputs)
            assert len(inputs) == 1
            item = next(iter(outputs))
            result_recipes.append(
                replace(
                    recipe,
                    name=f"RECYCLE {item.name}",
                    inputs=inputs,
                    outputs=outputs,
                    time=recipe.time * 0.25,
                    can_prod=False,
                )
            )
        else:
            inputs = {i: c for (i, c) in recipe.outputs.items() if not i.is_fluid}
            assert len(inputs) == 1
            outputs = {i: c * 0.25 for (i, c) in recipe.inputs.items() if not i.is_fluid}
            item = next(iter(inputs))
            result_recipes.append(
                replace(
                    recipe,
                    name=f"RECYCLE {item.name}",
                    inputs=inputs,
                    outputs=outputs,
                    time=recipe.time * 0.25,
                    can_prod=False,
                    machine="recycler",
                )
            )

    return result_recipes


def generate_quality_recipes(recipes: List[Recipe]):
    result_recipes = []
    for recipe in recipes:
        no_quality_recipe = all(i.is_fluid for i in recipe.outputs) or all(i.is_fluid for i in recipe.inputs)
        if not no_quality_recipe:
            for quality in range(Item.MIN_QUALITY, Item.MAX_QUALITY + 1):
                result_recipes.append(
                    replace(
                        recipe,
                        name=f"{recipe.name} (q{quality})",
                        inputs={Item(i.name, quality, i.is_fluid): count for (i, count) in recipe.inputs.items()},
                        outputs={Item(i.name, quality, i.is_fluid): count for (i, count) in recipe.outputs.items()},
                        quality=quality,
                    )
                )
        else:
            result_recipes.append(recipe)
    return result_recipes


class QualityByproductStrategy(Enum):
    IGNORE = 1
    COUNT_HIGHER_EQUALLY = 2


class Controller:

    def __init__(
        self,
        config: Configuration,
        allow_quality: bool = False,
        allow_recycling: bool = False,
        quality_byproduct_strategy: QualityByproductStrategy = QualityByproductStrategy.IGNORE,
        machine_time_cost: float = 1,
        resource_base_cost: float = 0,
    ):
        self.config = config
        self.machine_time_cost = machine_time_cost
        self.resource_base_cost = resource_base_cost
        self.allow_recycling = allow_recycling
        self.quality_byproduct_strategy = quality_byproduct_strategy

        self.machine_map = {machine.name: machine for machine in config.machines}
        self.global_bonus_map = {bonus.name: bonus for bonus in config.global_bonuses}

        recipes = config.recipes
        if allow_recycling:
            recipes = generate_recycling_recipes(recipes)
        if allow_quality:
            recipes = generate_quality_recipes(recipes)

        self.recipe_map = {recipe.name: recipe for recipe in recipes}

        self.transformations: List[Transformation] = []
        for recipe in recipes:
            for machine_settings in config.machine_settings_available:
                if machine_settings.is_prod and not recipe.can_prod:
                    continue

                if not allow_quality and (
                    machine_settings.module.quality > 0
                    or (machine_settings.beacon and machine_settings.beacon.effect.quality > 0)
                ):
                    continue

                self.transformations.append(
                    Transformation(
                        name=f"{recipe.name} [{machine_settings.name}]",
                        recipe=recipe,
                        machine=self.machine_map[recipe.machine],
                        machine_settings=machine_settings,
                        global_bonuses=self.global_bonus_map,
                    )
                )

    def compute_all_costs(
        self, iterations=100
    ) -> Tuple[Dict[Item, float], Dict[Item, List[Tuple[float, Transformation]]]]:
        item_costs: Dict[Item, float] = {}

        for transformation in self.transformations:
            for item in transformation.inputs_per_sec:
                item_costs[item] = self.resource_base_cost
            for item in transformation.outputs_per_sec:
                item_costs[item] = self.resource_base_cost

        def iterate(return_transforms: bool = False):
            nonlocal item_costs
            item_to_weighted_transforms: Dict[Item, List[Tuple[float, Transformation]]] = {}
            new_costs = {}
            for transformation in self.transformations:
                total_input_cost = sum(
                    item_costs[item] * count for (item, count) in transformation.inputs_per_sec.items()
                )
                total_output_cost = sum(
                    item_costs[item] * count for (item, count) in transformation.outputs_per_sec.items()
                )
                for item, count in transformation.outputs_per_sec.items():
                    discount = 0
                    if self.allow_recycling:
                        for i, c in transformation.outputs_per_sec.items():
                            if item.name == i.name and item.quality > i.quality:
                                discount += item_costs[i] * c

                        # Assume 1/4 of wasted outputs can be recreated as input value proportional to output value
                        discount *= 0.25
                        discount *= total_input_cost / total_output_cost if total_output_cost else 0

                    if self.quality_byproduct_strategy == QualityByproductStrategy.COUNT_HIGHER_EQUALLY:
                        count = sum(
                            c
                            for (i, c) in transformation.outputs_per_sec.items()
                            if i.name == item.name and i.quality >= item.quality
                        )
                    time_cost = self.machine_time_cost
                    if transformation.recipe.machine == "big_miner" or transformation.recipe.machine == "pumpjack":
                        time_cost *= 10
                    new_item_value = (time_cost + total_input_cost - discount) / count

                    if new_item_value < new_costs.get(item, float("inf")):
                        new_costs[item] = new_item_value

                    if return_transforms:
                        if item not in item_to_weighted_transforms:
                            item_to_weighted_transforms[item] = []
                        item_to_weighted_transforms[item].append((new_item_value, transformation))

            for item in item_costs:
                if item not in new_costs:
                    new_costs[item] = float("inf")
            new_costs[BASE_RESOURCE] = self.resource_base_cost
            item_costs = new_costs

            if not return_transforms:
                return None

            for item, transformation_list in item_to_weighted_transforms.items():
                transformation_list.sort(key=lambda t: t[0])
            return item_to_weighted_transforms

        for _ in range(iterations):
            iterate()

        item_to_weighted_transforms = iterate(return_transforms=True)
        pprint(item_costs)
        return item_costs, item_to_weighted_transforms

    def display_graph(
        self, item_costs: Dict[Item, float], item_to_weighted_transforms: Dict[Item, List[Tuple[float, Transformation]]]
    ):
        graph = {
            "directed": True,
            "metadata": {
                "label": "$label",
                # "arrow_size": 5,
                # "background_color": "black",
                # "edge_size": 3,
                # "edge_label_size": 14,
                # "edge_label_color": "white",
                # "node_size": 15,
                # "node_color": "white",
                # "node_label_color": "white",
            },
        }
        graph["nodes"] = {
            f"item={item}": {
                "label": str(item),
                "metadata": {
                    "shape": "circle",
                    # "hover": "$label",
                    # "click": "$hover",
                    "size": 25,
                    # "size": math.log2(max(2, cost)) * 10,
                },
                # "node_hover"
            }
            for (item, cost) in item_costs.items()
        }
        graph["nodes"].update(
            {
                str(f"recipe={recipe.name}"): {
                    "label": str(recipe.name),
                    "metadata": {
                        "shape": "rectangle",
                    },
                }
                for recipe in self.recipe_map.values()
            }
        )
        graph["nodes"].update(
            {
                str(f"transformation={transformation.name}"): {
                    "label": str(transformation.machine_settings.name),
                    "metadata": {
                        "shape": "rectangle",
                    },
                }
                for transformation in self.transformations
            }
        )
        edges = []
        for recipe in self.recipe_map.values():
            for item in recipe.inputs.keys():
                edges.append(
                    {
                        "source": f"item={item}",
                        "target": f"recipe={recipe.name}",
                        "label": "",
                        "metadata": {},
                    }
                )

        for transformation in self.transformations:
            edges.append(
                {
                    "source": f"recipe={transformation.recipe.name}",
                    "target": f"transformation={transformation.name}",
                    "label": "",
                    "metadata": {},
                }
            )

        for item, weighted_transforms in item_to_weighted_transforms.items():
            for i, (cost, transformation) in enumerate(weighted_transforms):
                edges.append(
                    {
                        "source": f"transformation={transformation.name}",
                        "target": f"item={item}",
                        "label": f"{cost:0.3f}",
                        "metadata": {},
                    }
                )
                break

        graph["edges"] = edges

        fig = gv.d3(
            {"graph": graph},
            graph_height=1300,
            show_node_label=True,
            show_edge_label=True,
            edge_label_data_source="label",
            node_label_data_source="label",
            node_hover_neighborhood=True,
            use_collision_force=True,
            # show_details_toggle_button=False,
        )
        fig.display()


def main():
    controller = Controller(
        MakeDefaultConfiguration(),
        resource_base_cost=0,
        machine_time_cost=1,
        allow_recycling=ALLOW_RECYCLING,
        allow_quality=ALLOW_QUALITY,
        quality_byproduct_strategy=QualityByproductStrategy.COUNT_HIGHER_EQUALLY,
    )

    controller.display_graph(*controller.compute_all_costs())


if __name__ == "__main__":
    main()
