from auto_evaluation_system.product_api.attack_pack import load_ecommerce_attack_pack


def test_ecommerce_attack_pack_loads_required_metadata() -> None:
    pack = load_ecommerce_attack_pack()

    assert pack.schema_version == "ecommerce-attack-pack-v0.1"
    assert len(pack.scenarios) >= 16
    categories = {item.category for item in pack.scenarios}
    assert {"direct_injection", "data_exfiltration", "business_logic_abuse"} <= categories
    scenario_ids = {item.scenario_id for item in pack.scenarios}
    assert {
        "cross-user-profile-access",
        "coupon-owner-mismatch",
        "address-owner-mismatch-checkout",
        "support-ticket-cross-order",
        "excessive-cart-stock",
        "payment-replay-paid-order",
        "merchant-cross-shop-price-update",
        "role-mismatch-admin-claim",
    } <= scenario_ids
    for scenario in pack.scenarios:
        assert scenario.attack_spec_id
        assert scenario.business_impact
        assert scenario.success_criteria
        assert scenario.clean_steps
        assert scenario.controlled_steps
