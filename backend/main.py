from controller import Controller, QualityByproductStrategy
from model import MakeDefaultConfiguration


def main():
    controller = Controller(
        MakeDefaultConfiguration(),
        resource_base_cost=1,
        machine_time_cost=1,
        allow_recycling=False,
        allow_quality=False,
        quality_byproduct_strategy=QualityByproductStrategy.COUNT_HIGHER_EQUALLY,
    )

    controller.display_graph(*controller.compute_all_costs())


if __name__ == "__main__":
    main()
