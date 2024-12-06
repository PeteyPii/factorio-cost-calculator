import math
from collections import defaultdict
from pprint import pprint

import gravis as gv
from model import (
    BASE_RESOURCE,
    ZERO_BONUS,
    Bonus,
    BonusMap,
    Configuration,
    Fluid,
    Item,
    ItemCounts,
    ItemKey,
    Machine,
    MachineSettings,
    MakeItem,
    Recipe,
)


def _Clamp(val, min, max):
    if min > max:
        raise ValueError("min > max")
    return min if val < min else max if val > max else val


class Transformation:

    def __init__(
        self,
        name: str,
        recipe: Recipe,
        recipe_bonuses: BonusMap,
        machine: Machine,
        machine_settings: MachineSettings,
        mining_bonus: Bonus,
    ):
        self.name = name
        self.recipe = recipe
        self.machine = machine
        self.machine_settings = machine_settings

        extra_effects = machine_settings.effect_total(machine) + recipe_bonuses.get(recipe.name, ZERO_BONUS)
        if recipe.is_mining:
            extra_effects += mining_bonus

        speed_multiplier = _Clamp(1.0 + extra_effects.speed, 0.2, math.inf)
        rate = machine.speed * speed_multiplier / recipe.time

        self.inputs_per_sec: ItemCounts = {}
        for item, count in recipe.inputs.items():
            self.inputs_per_sec[item] = count * rate

        productivty_multiplier = _Clamp(1.0 + extra_effects.productivity, 0, 1.0 + recipe.max_productivity)
        zero_quality_output_rate: ItemCounts = defaultdict(float)
        for item, count in recipe.outputs.items():
            zero_quality_output_rate[item] = count * rate * productivty_multiplier
        for item, count in recipe.outputs_no_productivity.items():
            zero_quality_output_rate[item] += count * rate

        # Deal with net totals:
        catalysts = set(self.inputs_per_sec.keys()) & set(recipe.outputs.keys())
        for catalyst in catalysts:
            if self.inputs_per_sec[catalyst] > zero_quality_output_rate[catalyst]:
                self.inputs_per_sec[catalyst] -= zero_quality_output_rate[catalyst]
                del zero_quality_output_rate[catalyst]
            elif self.inputs_per_sec[catalyst] < zero_quality_output_rate[catalyst]:
                zero_quality_output_rate[catalyst] -= self.inputs_per_sec[catalyst]
                del self.inputs_per_sec[catalyst]
            else:
                del zero_quality_output_rate[catalyst]
                del self.inputs_per_sec[catalyst]

        quality = _Clamp(extra_effects.quality, 0, math.inf)
        self.outputs_per_sec: ItemCounts = {
            Item(name=i.name, quality=recipe.quality): rate * (1 - quality)
            for (i, rate) in zero_quality_output_rate.items()
            if not i.is_fluid
        }
        self.outputs_per_sec.update(
            {Fluid(name=i.name): rate for (i, rate) in zero_quality_output_rate.items() if i.is_fluid}
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
                        Item(name=i.name, quality=curr_quality): rate * curr_multi
                        for (i, rate) in zero_quality_output_rate.items()
                        if not i.is_fluid
                    }
                )
                left_over -= curr_multi
                curr_quality += 1
                curr_multi *= 0.1

    def __repr__(self) -> str:
        return f"{self.name}"


def generate_quality_recipes(recipes: list[Recipe]):
    result_recipes = []
    for recipe in recipes:
        no_quality_recipe = all(i.is_fluid for i in recipe.outputs) or all(i.is_fluid for i in recipe.inputs)
        if not no_quality_recipe:
            for quality in range(Item.MIN_QUALITY, Item.MAX_QUALITY + 1):
                result_recipes.append(
                    recipe.model_copy(
                        deep=True,
                        update={
                            "name": f"{recipe.name}-q{quality}",
                            "inputs": {
                                MakeItem(i.name, quality, i.is_fluid): count for (i, count) in recipe.inputs.items()
                            },
                            "outputs": {
                                MakeItem(i.name, quality, i.is_fluid): count for (i, count) in recipe.outputs.items()
                            },
                            "quality": quality,
                        },
                    )
                )
        else:
            result_recipes.append(recipe)
    return result_recipes


class Controller:

    def __init__(self, config: Configuration):
        self.config = config

        recipes = config.recipes
        if config.enable_quality:
            recipes = generate_quality_recipes(recipes)

        if config.enable_recycling:
            self.recipe_map = {recipe.name: recipe for recipe in recipes}
        else:
            self.recipe_map = {
                recipe.name: recipe for recipe in recipes if "-recycling" not in recipe.name or "scrap" in recipe.name
            }

        self.transformations: list[Transformation] = []
        for recipe in self.recipe_map.values():
            for machine_settings in config.machine_settings_available:
                uses_prod_modules = machine_settings.module.productivity > 0 or (
                    machine_settings.beacon and machine_settings.beacon.effect.productivity > 0
                )
                if uses_prod_modules and not recipe.allow_productivity:
                    continue

                uses_quality_modules = machine_settings.module.quality > 0 or (
                    machine_settings.beacon and machine_settings.beacon.effect.quality > 0
                )
                if uses_quality_modules and (not self.config.enable_quality or not recipe.allow_quality):
                    continue

                if recipe.category not in config.machines:
                    continue

                self.transformations.append(
                    Transformation(
                        name=f"{recipe.name} [{machine_settings.name}]",
                        recipe=recipe,
                        machine=config.machines[recipe.category],
                        machine_settings=machine_settings,
                        recipe_bonuses=config.recipe_bonuses,
                        mining_bonus=config.mining_productivity,
                    )
                )

    def compute_all_costs(self, iterations=100) -> tuple[ItemCounts, dict[ItemKey, list[tuple[float, Transformation]]]]:
        item_costs: dict[ItemKey, float] = {}

        for transformation in self.transformations:
            for item in transformation.inputs_per_sec:
                item_costs[item] = self.config.resource_base_cost
            for item in transformation.outputs_per_sec:
                item_costs[item] = self.config.resource_base_cost

        def iterate(return_transforms: bool = False):
            nonlocal item_costs
            item_to_weighted_transforms: dict[ItemKey, list[tuple[float, Transformation]]] = {}
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
                    if self.config.enable_recycling:
                        for i, c in transformation.outputs_per_sec.items():
                            if item.name == i.name and item.quality > i.quality:
                                discount += item_costs[i] * c

                        # Assume 1/4 of wasted outputs can be recreated as input value proportional to output value
                        discount *= 0.25
                        discount *= total_input_cost / total_output_cost if total_output_cost else 0

                    # Always assume higher quality byproducts of the same item are at-least as good
                    # as the item we're considering
                    count = sum(
                        c
                        for (i, c) in transformation.outputs_per_sec.items()
                        if i.name == item.name and i.quality >= item.quality
                    )
                    time_cost = self.config.machine_time_cost
                    if transformation.recipe.is_mining:
                        time_cost *= 10
                    new_item_value = (time_cost + total_input_cost - discount) / count

                    if new_item_value < new_costs.get(item, math.inf):
                        new_costs[item] = new_item_value

                    if return_transforms:
                        if item not in item_to_weighted_transforms:
                            item_to_weighted_transforms[item] = []
                        item_to_weighted_transforms[item].append((new_item_value, transformation))

            for item in item_costs:
                if item not in new_costs:
                    new_costs[item] = math.inf
            new_costs[BASE_RESOURCE] = self.config.resource_base_cost
            item_costs = new_costs

            if not return_transforms:
                return None

            for item, transformation_list in item_to_weighted_transforms.items():
                transformation_list.sort(key=lambda t: t[0])
            return item_to_weighted_transforms

        for _ in range(iterations):
            iterate()

        item_to_weighted_transforms = iterate(return_transforms=True)
        table = [(k, v) for k, v in item_costs.items()]
        table.sort(key=lambda x: x[1])
        pprint(table)
        return item_costs, item_to_weighted_transforms

    def display_graph(
        self, item_costs: ItemCounts, item_to_weighted_transforms: dict[ItemKey, list[tuple[float, Transformation]]]
    ):
        graph = {
            "directed": True,
            "metadata": {
                "label": "$label",
                # "arrow_size": 5,
                # "background_color": "black",
                # "edge_size": 3,
                # "edge_label_size": 14,gi
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

    pass


if __name__ == "__main__":
    with open("default-config.json") as f:
        config = Configuration.model_validate_json(f.read())

    controller = Controller(config)
    controller.display_graph(*controller.compute_all_costs())
