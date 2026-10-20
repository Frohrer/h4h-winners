from scripts.build_catalog import category_for, dedupe_key, hair_types_in


def test_hair_types_from_ranges_and_codes():
    assert hair_types_in("Made for 3A-4C hair.") == ["3A", "3B", "3C", "4A", "4B", "4C"]
    assert hair_types_in("Hair Pattern: 4a-4c") == ["4A", "4B", "4C"]
    assert hair_types_in("works on 3a through 4c curls") == [
        "3A", "3B", "3C", "4A", "4B", "4C",
    ]  # fmt: skip
    assert hair_types_in("for 4A-4B, 4C 3A-C hair") == [
        "3A", "3B", "3C", "4A", "4B", "4C",
    ]  # fmt: skip
    assert hair_types_in("Great on 4C — a must for coils") == ["4C"]


def test_hair_types_from_families():
    assert hair_types_in("Hair Pattern: Wavy, Curly, Coily") == [
        "2A", "2B", "2C", "3A", "3B", "3C", "4A", "4B", "4C",
    ]  # fmt: skip
    assert hair_types_in("A light oil for straight & wavy textures.") == [
        "1A", "1B", "1C", "2A", "2B", "2C",
    ]  # fmt: skip


def test_no_hair_types_without_a_clear_statement():
    assert hair_types_in("Suitable for all hair types.") == []
    assert hair_types_in("Nº.4C Bond Maintenance Clarifying Shampoo") == []
    assert hair_types_in("Contains 2% salicylic acid") == []
    assert hair_types_in("Tames curly frizz") == []


def test_category():
    assert (
        category_for("cream", "styler (custard) Coil Sculpting Custard") == "Curl cream"
    )
    assert category_for("cream", "Whipped Shea Butter") == "Hair butter"
    assert category_for("shampoo", "Co-Wash Cleansing Conditioner") == "Co-wash"
    assert (
        category_for("serum", "Hair Regrowth Treatments Scalp Serum") == "Scalp serum"
    )
    assert category_for("leave_in", "Leave-In Conditioner") == "Leave-in conditioner"


def test_dedupe_key_ignores_case_brand_prefix_and_size():
    assert dedupe_key(
        "Mielle", "Pomegranate & Honey Leave-In Conditioner"
    ) == dedupe_key("MIELLE", "Mielle Pomegranate & Honey Leave In Conditioner, 12 oz")
