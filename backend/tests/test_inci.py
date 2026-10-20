"""Ingredient-label parsing, on the kinds of messy labels found in the scraped data."""

from app.engine.inci import display_name, ingredient_key, parse_inci


def test_header_batch_code_and_may_contain():
    raw = (
        "INGREDIENTS/INGRÉDIENTS: 1213537CD - Aqua/Water/Eau, Glycerin, Cetyl Alcohol,"
        " Parfum/Fragrance. May contain: CI 77891"
    )
    assert parse_inci(raw) == [
        "Aqua/Water/Eau",
        "Glycerin",
        "Cetyl Alcohol",
        "Parfum/Fragrance",
    ]


def test_organic_markers_and_footnote_tail():
    raw = (
        "*Organic Aloe Barbadensis Leaf Juice, Maltodextrin/VP Copolymer, Glycerin,"
        " **Fragrance, Citric Acid, Linalool.*Certified Organic **Plant-Derived Scent"
        " BlendOur formulas are continuously evaluated and may be updated over time."
    )
    assert parse_inci(raw) == [
        "Aloe Barbadensis Leaf Juice",
        "Maltodextrin/VP Copolymer",
        "Glycerin",
        "Fragrance",
        "Citric Acid",
        "Linalool",
    ]


def test_footnote_glued_to_last_name():
    raw = (
        "Aqua (Water/Eau), Cocamidopropyl Betaine, Glycerin, Sea Salt, Sorbic Acid,"
        " *Linalool, *Limonene*Natural component of Essential/Fragrance Oils"
    )
    assert parse_inci(raw)[-2:] == ["Linalool", "Limonene"]


def test_backslash_footnotes():
    raw = (
        "Aqua, Glycerin, \\Orbignya Oleifera (Babassu) Oil, Phenoxyethanol,"
        " Glycereth-2 Cocoate. \\Certified Organic Ingredients"
    )
    assert parse_inci(raw) == [
        "Aqua",
        "Glycerin",
        "Orbignya Oleifera (Babassu) Oil",
        "Phenoxyethanol",
        "Glycereth-2 Cocoate",
    ]


def test_list_pasted_twice_with_see_more():
    raw = (
        "Ingredients: Aqua/Water/Eau, Glycerin, Aloe Barbadensis Leaf Juice, Cetyl Alcohol,"
        " Limonene.Ingredients: Aqua/Water/Eau, Glycerin, Aloe Barbadensis Leaf…  See more"
    )
    assert parse_inci(raw) == [
        "Aqua/Water/Eau",
        "Glycerin",
        "Aloe Barbadensis Leaf Juice",
        "Cetyl Alcohol",
        "Limonene",
    ]


def test_bullets():
    raw = "Aqua • Sodium Laureth Sulfate •Cocamidopropyl Betaine · Sodium Chloride • Parfum"
    assert parse_inci(raw) == [
        "Aqua",
        "Sodium Laureth Sulfate",
        "Cocamidopropyl Betaine",
        "Sodium Chloride",
        "Parfum",
    ]


def test_commas_inside_parentheses_and_numbers_stay_put():
    raw = (
        "Aqua (Water, Eau), Cetearyl Alcohol, Behentrimonium Methosulfate (and) Cetearyl"
        " Glucoside, 1,2-Hexanediol, Caprylyl Glycol"
    )
    assert parse_inci(raw) == [
        "Aqua (Water, Eau)",
        "Cetearyl Alcohol",
        "Behentrimonium Methosulfate",
        "Cetearyl Glucoside",
        "1,2-Hexanediol",
        "Caprylyl Glycol",
    ]


def test_list_without_commas_split_after_function():
    raw = (
        "Water (Solvent) Glycerin (Humectant) Cetyl Alcohol (Emollient)"
        " Phenoxyethanol (Preservative)"
    )
    assert parse_inci(raw) == [
        "Water (Solvent)",
        "Glycerin (Humectant)",
        "Cetyl Alcohol (Emollient)",
        "Phenoxyethanol (Preservative)",
    ]


def test_fil_code_and_directions_end_the_list():
    assert parse_inci(
        "Aqua, Sodium Laureth Sulfate, Coco-Betaine, Parfum, Limonene. F.I.L. D238909/1"
    ) == ["Aqua", "Sodium Laureth Sulfate", "Coco-Betaine", "Parfum", "Limonene"]
    assert (
        parse_inci(
            "Aqua, Glycerin, Panthenol, Parfum, Citric Acid, Sodium Benzoate."
            " Anwendung: Auf das nasse Haar auftragen"
        )[-1]
        == "Sodium Benzoate"
    )


def test_marketing_prose_before_the_list():
    raw = (
        "Gentle Blend of Coconut Oil-Derived Surfactants Provides an easy, abundant lather"
        " that leaves the scalp and hair feeling hydrated. No.4 BOND MAINTENANCE SHAMPOO:"
        " Aqua (Water, Eau), Sodium Lauroyl Methyl Isethionate, Cocamidopropyl Betaine,"
        " Glycerin, Parfum"
    )
    assert parse_inci(raw) == [
        "Aqua (Water, Eau)",
        "Sodium Lauroyl Methyl Isethionate",
        "Cocamidopropyl Betaine",
        "Glycerin",
        "Parfum",
    ]


def test_percentages_and_lot_numbers_are_stripped():
    raw = "1166061 A - AQUA/WATER, 2% Glycerin, Cetyl Alcohol - 1.0%, Parfum, Limonene"
    assert parse_inci(raw) == [
        "AQUA/WATER",
        "Glycerin",
        "Cetyl Alcohol",
        "Parfum",
        "Limonene",
    ]


def test_not_a_list():
    assert parse_inci(None) == []
    assert parse_inci("Tea tree") == ["Tea tree"]
    assert parse_inci("12345, 67") == []


def test_water_and_fragrance_spellings_share_one_id():
    for spelling in ["Aqua", "Water", "Aqua/Water/Eau", "Water (Aqua)", "AQUA / WATER"]:
        assert ingredient_key(spelling) == "water"
    assert ingredient_key("Aqua (Deionized Water)") == "water"
    assert ingredient_key("Parfum/Fragrance") == "fragrance"
    assert ingredient_key("Fragrance (Parfum)") == "fragrance"
    assert ingredient_key("Rose Water") != "water"
    assert ingredient_key("Cetearyl  Alcohol.") == "cetearyl-alcohol"
    assert ingredient_key("CETEARYL ALCOHOL") == "cetearyl-alcohol"


def test_display_name():
    assert display_name("Butyrospermum Parkii (Shea) Butter") == "Shea butter"
    assert display_name("Ricinus Communis (Castor) Seed Oil") == "Castor seed oil"
    assert display_name("CETEARYL ALCOHOL") == "Cetearyl alcohol"
    assert (
        display_name("PEG-40 Hydrogenated Castor Oil")
        == "PEG-40 hydrogenated castor oil"
    )
    assert (
        display_name("Hydrolyzed Adansonia Digitata (Baobab) Seed Protein")
        == "Hydrolyzed adansonia digitata (baobab) seed protein"
    )


def test_marketing_text_is_not_an_ingredient():
    assert parse_inci(
        "Our all-new aloe & honey deep conditioner, Water, Glycerin, Honey, Cetyl Alcohol"
    ) == ["Water", "Glycerin", "Honey", "Cetyl Alcohol"]
