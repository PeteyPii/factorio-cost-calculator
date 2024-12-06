import itertools
import json
import math
import re
from typing import Annotated, Any, ClassVar, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    PlainSerializer,
    WithJsonSchema,
)


class Item(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    quality: int = 1
    is_fluid: bool = False

    MIN_QUALITY: ClassVar[int] = 1
    MAX_QUALITY: ClassVar[int] = 5

    QUALITY_SUFFIX: ClassVar[dict[int, str]] = {
        1: "q1",
        2: "q2",
        3: "q3",
        4: "q4",
        5: "q5",
    }

    def serialize(self) -> str:
        if self.is_fluid:
            return f"fluid-{self.name}"
        elif self.quality == 1:
            return f"{self.name}"
        else:
            return f"{self.name}-q{self.quality}"

    @staticmethod
    def deserialize(data: Any) -> str:
        if not isinstance(data, str):
            return data

        if data.startswith("fluid-"):
            return Item(name=data.removeprefix("fluid-"), is_fluid=True)
        match = re.match(r"(.*)-q(\d+)", data)
        if match is not None:
            return Item(name=match[1], quality=int(match[2]))
        return Item(name=data)

    def __str__(self) -> str:
        return self.serialize()


ItemKey = Annotated[
    Item,
    BeforeValidator(lambda item: Item.deserialize(item)),
    PlainSerializer(lambda item: item.serialize(), return_type=str),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]

ItemCounts = dict[ItemKey, float]


def MakeItem(name: str, quality: int = Item.MIN_QUALITY, is_fluid: bool = False):
    if is_fluid:
        return Fluid(name=name)
    return Item(name=name, quality=quality)


def Fluid(name: str) -> Item:
    return Item(name=name, is_fluid=True)


class Recipe(BaseModel):
    model_config = ConfigDict(ser_json_inf_nan="strings")

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


class Bonus(BaseModel):
    name: str
    speed: float = 0.0
    productivity: float = 0.0
    quality: float = 0.0

    def __add__(self, other: Self) -> Self:
        return Bonus(
            name="",
            speed=self.speed + other.speed,
            productivity=self.productivity + other.productivity,
            quality=self.quality + other.quality,
        )

    def __mul__(self, scale: float) -> Self:
        return Bonus(
            name=self.name,
            speed=self.speed * scale,
            productivity=self.productivity * scale,
            quality=self.quality * scale,
        )

    def __rmul__(self, scale: float) -> Self:
        return self.__mul__(scale)


ZERO_BONUS = Bonus(name="zero")

BonusMap = dict[str, Bonus]


class Beacon(BaseModel):
    name: str
    transmission: float
    effect: Bonus


class Machine(BaseModel):
    name: str
    speed: float = 1.0
    module_slots: int = 0
    base_effect: Bonus = ZERO_BONUS

    def __lt__(self, other: Self):
        if self.name == "biochamber":
            return other.name != "biochamber"
        if self.speed != other.speed:
            return self.speed < other.speed
        if self.module_slots != other.module_slots:
            return self.module_slots < other.module_slots
        return False


class MachineSettings(BaseModel):
    name: str
    module: Bonus  # only one type of module per machine
    num_beacons: int = 0
    beacon: Beacon | None = None

    def effect_total(self, machine: Machine) -> Bonus:
        effect = machine.base_effect + self.module * machine.module_slots
        if self.beacon and self.num_beacons:
            effect += (self.beacon.transmission * (self.num_beacons**0.5)) * self.beacon.effect
        return effect


class Configuration(BaseModel):
    name: str
    enable_quality: bool = False
    enable_recycling: bool = False
    machine_time_cost: float = 1.0
    resource_base_cost: float = 1.0
    machines: dict[str, Machine]
    machine_settings_available: list[MachineSettings]
    mining_productivity: Bonus
    recipe_bonuses: BonusMap
    recipes: list[Recipe]


BASE_RESOURCE = Item(name="resource")


def _OutputMaps(products) -> tuple[ItemCounts, ItemCounts]:
    outputs = {}
    outputs_no_prod = {}
    for product in products:
        expected = product.get("amount")
        if expected is None:
            expected = (product["amount_min"] + product["amount_max"]) * 0.5
        expected *= product.get("probability", 1.0)
        item = Item(name=product["name"], is_fluid=product["type"] == "fluid")
        if product.get("ignored_by_productivity", 0) > expected:
            outputs[item] = 0
            outputs_no_prod[item] = expected
        elif product.get("ignored_by_productivity", 0) > 0:
            outputs[item] = expected - product.get("ignored_by_productivity", 0)
            outputs_no_prod[item] = product.get("ignored_by_productivity", 0)
        else:
            outputs[item] = expected

    return outputs, outputs_no_prod


def LoadDataDumpRecipes(prototypes: dict[Any, Any]) -> list[Recipe]:
    recipes = []

    for r in prototypes["resource"].values():
        minable = r["minable"]
        inputs = {BASE_RESOURCE: 1}
        if "required_fluid" in minable:
            # Not sure why the prototype says 10x the actual fluid needed...
            inputs[Fluid(name=minable["required_fluid"])] = minable["fluid_amount"] * 0.1
        if "results" in minable:
            outputs, outputs_no_prod = _OutputMaps(minable["results"])
        else:
            outputs = {}
            outputs[Item(name=minable["result"])] = float(minable.get("count", 1))
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
            inputs[Fluid(name=minable["required_fluid"])] = minable["fluid_amount"] * 0.1
        if "results" in minable:
            outputs, outputs_no_prod = _OutputMaps(minable["results"])
        else:
            outputs = {}
            outputs[Item(name=minable["result"])] = float(minable.get("count", 1))
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
            inputs[Fluid(name=minable["required_fluid"])] = minable["fluid_amount"] * 0.1
        if "results" in minable:
            outputs, outputs_no_prod = _OutputMaps(minable["results"])
        else:
            outputs = {}
            outputs[Item(name=minable["result"])] = float(minable.get("count", 1))
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
        inputs = {Item(name=i["name"], is_fluid=i["type"] == "fluid"): i["amount"] for i in r.get("ingredients", [])}
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


def LoadDataDumpMachines(prototypes: dict[Any, Any]) -> dict[str, Machine]:
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
            "low-density_structure": 10 * Bonus(name="lds_productivity", productivity=0.1),
            "casting-low-density_structure": 10 * Bonus(name="lds_productivity", productivity=0.1),
            # TODO: rest of these
        },
        machines=machines,
        machine_settings_available=[
            # MachineSettings(
            #     name="none",
            #     num_beacons=0,
            #     module=ZERO_BONUS,
            # ),
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
    config = MakeDefaultConfiguration()
    with open("default-config.json", "w") as f:
        f.write(config.model_dump_json(indent=2))
