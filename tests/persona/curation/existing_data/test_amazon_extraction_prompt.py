from persona.human_extraction.scripts import run_one_amazon_openrouter


def test_amazon_openrouter_prompt_defaults_to_unsupported_and_blocks_sensitive_guessing():
    prompt = run_one_amazon_openrouter.build_amazon_prompt(
        "REVIEWER HISTORY TEXT",
        [
            {
                "id": "age_bracket",
                "label": "Age bracket",
                "description": "Age range.",
                "values": ["18-24", "25-34"],
            },
            {
                "id": "domain",
                "label": "Domain",
                "description": "Interest or expertise domain.",
                "values": ["Cooking", "Books"],
            },
        ],
    )

    assert 'start from value=null and assignment_type="unsupported"' in prompt
    assert "non-null value only from an explicit self-statement" in prompt
    assert "Do not use product category alone" in prompt
    assert "requires a repeated pattern across at least 3 distinct reviews" in prompt
    assert "Most dimensions can be unsupported. Do not make the persona complete." in prompt
    assert "a softer inference from the overall pattern" not in prompt
