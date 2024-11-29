import dataclasses
import itertools
import json
import math
from pprint import pprint
from typing import Any, ClassVar, Dict, List, Optional, Self, Tuple


@dataclasses.dataclass(frozen=True, order=True, init=False)
class Item:
    name: str
    quality: int = 1
    is_fluid: bool = False

    MIN_QUALITY: ClassVar[int] = 1
    MAX_QUALITY: ClassVar[int] = 5

    QUALITY_SUFFIX: ClassVar[Dict[int, str]] = {
        # 1: "‧",
        # 2: "⁚",
        # 3: "⁖",
        # 4: "⁘",
        # 5: "⁙",
        1: "q1",
        2: "q2",
        3: "q3",
        4: "q4",
        5: "q5",
    }

    def __init__(self, name: str, quality: int = MIN_QUALITY, is_fluid: bool = False):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "quality", quality if not is_fluid else Item.MIN_QUALITY)
        object.__setattr__(self, "is_fluid", is_fluid)

    def __repr__(self):
        if self.is_fluid:
            return f"{self.name}"
        elif self.quality > Item.MIN_QUALITY:
            return f"{self.name}-q{self.quality}"
        else:
            return f"{self.name}"

    def __str__(self):
        if self.is_fluid:
            return f"{self.name}"
        elif self.quality > Item.MIN_QUALITY:
            return f"{self.name}-{Item.QUALITY_SUFFIX[self.quality]}"
        else:
            return f"{self.name}"


def Fluid(name: str) -> Item:
    return Item(name, is_fluid=True)


ItemCounts = Dict[Item, float]


@dataclasses.dataclass
class Recipe:
    name: str
    category: str
    time: float
    inputs: ItemCounts
    outputs: ItemCounts
    outputs_no_productivity: ItemCounts
    quality: int = Item.MIN_QUALITY
    allow_productivity: bool = True
    allow_quality: bool = True
    max_productivity: float = 3.0
    is_mining: bool = False


@dataclasses.dataclass
class Bonus:
    name: str
    speed: float = 0
    productivity: float = 0
    quality: float = 0

    def __add__(self, other: Self) -> Self:
        return Bonus(
            name="",
            speed=self.speed + other.speed,
            productivity=self.productivity + other.productivity,
            quality=self.quality + other.quality,
        )

    def __mul__(self, scale: float) -> Self:
        return Bonus(
            self.name, speed=self.speed * scale, productivity=self.productivity * scale, quality=self.quality * scale
        )

    def __rmul__(self, scale: float) -> Self:
        return self.__mul__(scale)


ZERO_BONUS = Bonus(name="zero")

BonusMap = Dict[str, Bonus]


@dataclasses.dataclass
class Beacon:
    name: str
    transmission: float
    effect: Bonus


@dataclasses.dataclass
class Machine:
    name: str
    speed: float = 1
    module_slots: int = 0
    base_effect: Bonus = dataclasses.field(default_factory=lambda: ZERO_BONUS)

    def __lt__(self, other: Self):
        if self.name == "biochamber":
            return other.name != "biochamber"
        if self.speed != other.speed:
            return self.speed < other.speed
        if self.module_slots != other.module_slots:
            return self.module_slots < other.module_slots
        return False


@dataclasses.dataclass
class MachineSettings:
    name: str
    module: Bonus  # only one type of module per machine
    num_beacons: int = 0
    beacon: Optional[Beacon] = None

    def effect_total(self, machine: Machine) -> Bonus:
        effect = self.module * machine.module_slots
        if self.beacon and self.num_beacons:
            effect += (self.beacon.transmission * (self.num_beacons**0.5)) * self.beacon.effect
        return effect


@dataclasses.dataclass
class Configuration:
    name: str
    recipes: List[Recipe]
    recipe_bonuses: Dict[str, Bonus]
    machines: Dict[str, Machine]
    machine_settings_available: List[MachineSettings]
    mining_productivity: Bonus


BASE_RESOURCE = Item("resource", is_fluid=True)


def _OutputMaps(products) -> Tuple[ItemCounts, ItemCounts]:
    outputs = {}
    outputs_no_prod = {}
    for product in products:
        expected = product.get("amount")
        if expected is None:
            expected = (product["amount_min"] + product["amount_max"]) * 0.5
        expected *= product.get("probability", 1.0)
        item = Item(product["name"], is_fluid=product["type"] == "fluid")
        if product.get("ignored_by_productivity", 0) > expected:
            outputs[item] = 0
            outputs_no_prod[item] = expected
        else:
            outputs[item] = expected - product.get("ignored_by_productivity", 0)
            outputs_no_prod[item] = product.get("ignored_by_productivity", 0)
    return outputs, outputs_no_prod


def LoadDataDumpRecipes(prototypes: Dict[Any, Any]) -> List[Recipe]:
    recipes = []

    for r in prototypes["resource"].values():
        minable = r["minable"]
        inputs = {BASE_RESOURCE: 1}
        if "required_fluid" in minable:
            # Not sure why the prototype says 10x the actual fluid needed...
            inputs[Fluid(minable["required_fluid"])] = minable["fluid_amount"] * 0.1
        if "results" in minable:
            outputs, outputs_no_prod = _OutputMaps(minable["results"])
        else:
            outputs = {}
            outputs[Item(minable["result"])] = float(minable.get("count", 1))
            outputs_no_prod = {}
        recipes.append(
            Recipe(
                name=r["name"],
                category=r.get("category", "basic-solid"),
                time=minable["mining_time"],
                inputs=inputs,
                outputs=outputs,
                outputs_no_productivity=outputs_no_prod,
                max_productivity=math.inf,
                allow_productivity=True,
                allow_quality=True,
                is_mining=True,
            )
        )

    for p in prototypes["plant"].values():
        minable = p["minable"]
        inputs = {BASE_RESOURCE: 1}
        if "required_fluid" in minable:
            # Not sure why the prototype says 10x the actual fluid needed...
            inputs[Fluid(minable["required_fluid"])] = minable["fluid_amount"] * 0.1
        if "results" in minable:
            outputs, outputs_no_prod = _OutputMaps(minable["results"])
        else:
            outputs = {}
            outputs[Item(minable["result"])] = float(minable.get("count", 1))
            outputs_no_prod = {}
        recipes.append(
            Recipe(
                name=p["name"],
                category="agricultural-tower",
                time=60 / p["growth_ticks"],
                inputs=inputs,
                outputs=outputs,
                outputs_no_productivity=outputs_no_prod,
                max_productivity=0,
                allow_productivity=False,
                allow_quality=False,
                is_mining=False,
            )
        )

    for p in prototypes["asteroid-chunk"].values():
        if "minable" not in p:
            continue
        minable = p["minable"]
        inputs = {BASE_RESOURCE: 1}
        if "required_fluid" in minable:
            # Not sure why the prototype says 10x the actual fluid needed...
            inputs[Fluid(minable["required_fluid"])] = minable["fluid_amount"] * 0.1
        if "results" in minable:
            outputs, outputs_no_prod = _OutputMaps(minable["results"])
        else:
            outputs = {}
            outputs[Item(minable["result"])] = float(minable.get("count", 1))
            outputs_no_prod = {}
        recipes.append(
            Recipe(
                name=p["name"],
                category="asteroid-collector",
                time=1,  # TODO: come up with something reasonable
                inputs=inputs,
                outputs=outputs,
                outputs_no_productivity=outputs_no_prod,
                max_productivity=0,
                allow_productivity=False,
                allow_quality=False,
                is_mining=False,
            )
        )

    for r in prototypes["recipe"].values():
        inputs = {Item(i["name"], is_fluid=i["type"] == "fluid"): i["amount"] for i in r.get("ingredients", [])}
        results = r.get("results", [])
        outputs, outputs_no_prod = _OutputMaps(results)
        recipes.append(
            Recipe(
                name=r["name"],
                category=r.get("category", "crafting"),
                time=r.get("energy_required", 0.5),
                inputs=inputs,
                outputs=outputs,
                outputs_no_productivity=outputs_no_prod,
                max_productivity=r.get("maximum_productivity", 3.0),
                allow_productivity=r.get("allow_productivity", False),
                allow_quality=r.get("allow_quality", True),
            )
        )

    pumped_fluids = set()
    for t in prototypes["tile"].values():
        if "fluid" not in t:
            continue
        if t["fluid"] in pumped_fluids:
            continue
        pumped_fluids.add(t["fluid"])
        recipes.append(
            Recipe(
                name=f"offshore-pump-{t["fluid"]}",
                category="offshore-pump",
                time=1.0,
                inputs={},
                outputs={Fluid(t["fluid"]): 1.0},
                outputs_no_productivity={},
                allow_productivity=False,
                allow_quality=False,
            )
        )

    recipes = [r for r in recipes if "parameter" not in r.name]
    recipes = [r for r in recipes if "bpsb" not in r.name]
    recipes = [r for r in recipes if "unknown" not in r.name]

    return recipes


def LoadDataDumpMachines(prototypes: Dict[Any, Any]) -> Dict[str, Machine]:
    machines = {}
    for m in itertools.chain(
        prototypes["assembling-machine"].values(), prototypes["furnace"].values(), prototypes["mining-drill"].values()
    ):
        effects = m.get("effect_receiver", {}).get("base_effect", {})
        base_effect = Bonus(
            name="base",
            speed=effects.get("speed", 0.0),
            productivity=effects.get("productivity", 0.0),
            quality=effects.get("quality", 0.0),
        )
        machine = Machine(
            name=m["name"],
            speed=m.get("crafting_speed") or m.get("mining_speed"),
            module_slots=m.get("module_slots", 0),
            base_effect=base_effect,
        )
        for category in m.get("crafting_categories", []) + m.get("resource_categories", []):
            if category not in machines:
                machines[category] = machine
                continue

            machines[category] = max(machine, machines[category])

    p = prototypes["offshore-pump"]["offshore-pump"]
    machines["offshore-pump"] = Machine(
        name=p["name"],
        speed=p["pumping_speed"],
    )

    t = prototypes["agricultural-tower"]["agricultural-tower"]
    farming_diameter = t["radius"] * 2 + 1
    machines["agricultural-tower"] = Machine(
        name=t["name"],
        speed=farming_diameter**2 - 1,
    )

    c = prototypes["asteroid-collector"]["asteroid-collector"]
    machines["asteroid-collector"] = Machine(
        name=c["name"],
        speed=c["arm_speed_base"] * c["arm_count_base"],
    )

    return machines


def MakeDefaultConfiguration() -> Configuration:

    speed_module = Bonus(name="speed_3", speed=0.5, quality=-0.025)
    prod_module = Bonus(name="prod_3", productivity=0.1, speed=-0.15)
    # prod_module = Bonus(name="legendary_prod_3", prod=0.25, speed=-0.15)
    # quality_module = Bonus(name="quality_3", quality=0.025, speed=-0.05)
    quality_module = Bonus(name="legendary_quality_3", quality=0.062, speed=-0.05)

    with open("data-raw-dump.json") as f:
        prototypes = json.load(f)

    recipes = LoadDataDumpRecipes(prototypes)
    machines = LoadDataDumpMachines(prototypes)

    config = Configuration(
        name="default",
        recipes=recipes,
        recipe_bonuses={
            "steel-plate": 10 * Bonus(name="steel_productivity", productivity=0.1),
            "casting-steel": 10 * Bonus(name="steel_productivity", productivity=0.1),
            "low-density_structure": 10 * Bonus(name="steel_productivity", productivity=0.1),
            "casting-low-density_structure": 10 * Bonus(name="steel_productivity", productivity=0.1),
            # TODO: rest of these
        },
        machines=machines,
        machine_settings_available=[
            MachineSettings(
                name="none",
                num_beacons=0,
                module=ZERO_BONUS,
            ),
            MachineSettings(
                name="quality",
                num_beacons=0,
                module=quality_module,
            ),
            MachineSettings(
                name="balanced",
                num_beacons=8,
                beacon=Beacon(name="speed", transmission=1.5, effect=2 * speed_module),
                module=prod_module,
            ),
            MachineSettings(
                name="speed",
                num_beacons=8,
                beacon=Beacon(name="speed", transmission=1.5, effect=2 * speed_module),
                module=speed_module,
            ),
        ],
        mining_productivity=100 * Bonus(name="mining_productivity", productivity=0.1),
    )

    return config


if __name__ == "__main__":
    with open("data-raw-dump.json") as f:
        prototypes = json.load(f)
    recipes = LoadDataDumpRecipes(prototypes)
    recipe_names = [r.name for r in recipes]
    recipe_names.sort()
    pprint(recipe_names)

    machines = LoadDataDumpMachines(prototypes)
    machine_names = {category: machine.name for category, machine in machines.items()}
    pprint(machine_names)
