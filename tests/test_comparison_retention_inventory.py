from app.config import settings
from app.retention.factory import build_inventory


def test_comparison_root_is_counted_but_not_a_deletion_port() -> None:
    inventory = build_inventory(destructive_supported=False)
    roots = dict(inventory.config.roots)

    assert roots["comparisons"] == settings.comparison_root.resolve()
    # InventoryConfig 只有容量统计配置，不会因为加入 root 就获得删除能力。
    assert inventory.config.destructive_gc_supported is False
