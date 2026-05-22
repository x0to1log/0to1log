from services.agents.prompts_news_pipeline import (
    CLASSIFICATION_SYSTEM_PROMPT,
    QUALITY_CHECK_BUSINESS_BEGINNER,
    QUALITY_CHECK_BUSINESS_EXPERT,
    QUALITY_CHECK_BUSINESS_LEARNER,
    QUALITY_CHECK_FRONTLOAD,
    QUALITY_CHECK_RESEARCH_BEGINNER,
    QUALITY_CHECK_RESEARCH_EXPERT,
    QUALITY_CHECK_RESEARCH_LEARNER,
    QUALITY_CHECK_WEEKLY_EXPERT,
    QUALITY_CHECK_WEEKLY_LEARNER,
    get_digest_prompt,
    get_digest_quiz_prompt,
    get_weekly_ko_prompt,
    get_weekly_prompt,
)


def test_research_expert_prompt_is_technical_brief():
    prompt = get_digest_prompt("research", "expert", [])

    assert "## LLM & SOTA Models" in prompt
    assert "## Open Source & Repos" in prompt
    assert "## Research Papers" in prompt
    assert "## Why It Matters" in prompt
    assert "## Technical Decision Points" not in prompt
    assert "## Strategic Decisions" not in prompt


def test_research_learner_prompt_stays_curated_not_action_driven():
    prompt = get_digest_prompt("research", "learner", [])

    assert "## LLM & SOTA Models" in prompt
    assert "## Open Source & Repos" in prompt
    assert "## Research Papers" in prompt
    assert "## Why It Matters" in prompt
    assert "## What To Try This Week" not in prompt
    assert "## Action Items" not in prompt
    assert "guided technical digest" in prompt


def test_research_beginner_prompt_uses_dedicated_context_explainer_format():
    prompt = get_digest_prompt("research", "beginner", [])

    assert "Beginner persona" in prompt
    assert "Main item cap: Research Beginner 1-2 main `###` items; Business Beginner 1-2 main `###` items" in prompt
    assert "Main 2 limit: choose no more than 2 main `###` items" in prompt
    assert "Problem first: the first paragraph after every main `###` heading must explain" in prompt
    assert "First-paragraph term budget: the first paragraph after each main `###` heading may use at most 2 countable domain terms" in prompt
    assert "Do not count company names, product names, source names" in prompt
    assert "Do not remove important terms; delay them until the reader has the problem frame" in prompt
    assert "Research Beginner main_items: 1-2" in prompt
    assert "Research one_line should use at most 2 technical terms" in prompt
    assert "plain consequence before adding more detail" in prompt
    assert "Problem first: open each main item by explaining the plain problem" in prompt
    assert "First-paragraph term budget: use at most 2 countable research/security terms" in prompt
    assert "later paragraphs may carry the necessary technical names" in prompt
    assert "short but not shallow" in prompt
    assert "one setup sentence and one consequence sentence" in prompt
    assert "what burden is reduced or what new risk/check burden is exposed" in prompt
    assert "무엇이 쉬워졌나 / 무엇을 더 조심해야 하나" in prompt
    assert "Do not turn every input group into a full section" in prompt
    assert "## Context First" in prompt
    assert "## 먼저 알면 좋은 배경" in prompt
    assert "## Main Research to Understand Today" in prompt
    assert "## 오늘 꼭 이해할 연구" in prompt
    assert "## Worth Skimming" in prompt
    assert "## 가볍게 지나가도 되는 소식" in prompt
    assert "## Read the Learner Digest Next" in prompt
    assert "## 학습자 뉴스 이어읽기" in prompt
    assert "Never copy schema labels as field content" in prompt
    assert "Action Items" not in prompt


def test_business_beginner_prompt_uses_lens_sentence_not_catalog():
    prompt = get_digest_prompt("business", "beginner", [])

    assert "Business Beginner main_items: 1-2" in prompt
    assert "Main 2 limit: choose no more than 2 main `###` items" in prompt
    assert "Problem first: open each main item by explaining the plain business problem" in prompt
    assert "First-paragraph term budget: use at most 2 countable business/infrastructure terms" in prompt
    assert "Do not count company names, product names, source names" in prompt
    assert "Delay extra technical names to paragraph 2" in prompt
    assert "Business one_line is a lens sentence, not a catalog" in prompt


def test_business_beginner_prompt_does_not_force_abstract_theme_connections():
    prompt = get_digest_prompt("business", "beginner", [])

    assert "Do not force unrelated stories into one abstract theme" in prompt
    assert "Explain each main story's concrete product or business change first" in prompt
    assert "Use a shared theme only after the concrete changes are clear" in prompt
    assert "keep it as context, not the lead explanation for an unrelated product story" in prompt
    assert "cite the primary product or company source before secondary commentary" in prompt


def test_research_beginner_prompt_limits_method_name_stacking_after_problem_frame():
    prompt = get_digest_prompt("research", "beginner", [])

    assert "Do not place more than two method, model, benchmark, or dataset names in the same paragraph" in prompt
    assert "move the extras to Worth Skimming or the learner-digest bridge" in prompt
    assert "The first sentence after each main research heading should state the plain problem without acronyms or method names" in prompt
    assert "If a method name is necessary, pair it with its role, not a full definition" in prompt


def test_beginner_prompts_frame_learner_bridge_as_editorial_pointer():
    for digest_type in ["research", "business"]:
        prompt = get_digest_prompt(digest_type, "beginner", [])

        assert "Do not write direct reading instructions inside the learner bridge body" in prompt
        assert "Frame the learner bridge as an editorial pointer" in prompt


def test_weekly_beginner_prompt_uses_context_first_four_story_contract():
    prompt = get_weekly_prompt("beginner")
    learner_prompt = get_weekly_prompt("learner")

    assert prompt != learner_prompt
    assert "Weekly Beginner AI News" in prompt
    assert "same weekly edition covered by learner and expert" in prompt
    assert "Pick exactly 4 main stories" in prompt
    assert "TWO shared weekly anchor stories" in prompt
    assert "ONE everyday adoption story" in prompt
    assert "ONE research-digest story" in prompt
    assert "selection labels must only appear in story_selection_notes" in prompt
    assert "## Start Here" in prompt
    assert "## The 4 Stories That Matter" in prompt
    assert "## What Not To Over-Assume" in prompt


def test_weekly_beginner_ko_prompt_uses_beginner_section_headings():
    prompt = get_weekly_ko_prompt("beginner")

    assert "## 이번 주 한 줄" in prompt
    assert "## 여기서 시작하기" in prompt
    assert "## 꼭 알아둘 이야기 4개" in prompt
    assert "## 과하게 받아들이지 말아야 할 것" in prompt
    assert "## 학습자 버전을 읽어봐도 좋은 때" in prompt
    assert "selection labels" in prompt
    assert "story_selection_notes_ko" in prompt
    assert "Keep the same story selection, same order, same citations" in prompt
    assert "Preserve `answer_index` exactly" in prompt
    assert "weekly_quiz_ko" in prompt


def test_daily_writer_prompt_no_longer_generates_quiz_fields():
    prompt = get_digest_prompt("research", "beginner", [])

    assert "quiz_en" not in prompt
    assert "quiz_ko" not in prompt
    assert "Quiz consistency guard" not in prompt


def test_digest_quiz_prompt_makes_beginner_quiz_a_misconception_check_not_recall():
    for digest_type in ["research", "business"]:
        prompt = get_digest_quiz_prompt(digest_type, "en")

        assert "English quiz" in prompt
        assert "Produce these three keys exactly: expert, learner, beginner" in prompt
        assert "Do not use Korean text" in prompt
        assert "misconception check, not recall" in prompt
        assert "Do not ask about trivia that is only a number, date, product name, benchmark score, funding amount, CVE count, or company name" in prompt
        assert "The correct option is the safest interpretation of the digest's beginner lens" in prompt
        assert "Prefer asking for the safest takeaway from the digest" in prompt
        assert "Avoid questions where multiple options can be interpreted as reasonable warnings" in prompt
        assert "Avoid wording the question as a negative warning if that makes several options sound partly true" in prompt
        assert "Do not ask beginner questions in the form \"which misunderstanding should readers avoid\"" in prompt
        assert "Beginner correct options must state one single safe takeaway, not combine two warnings with and/or" in prompt
        assert "Wrong options should be plausible beginner mistakes" in prompt
        assert "Wrong options must stay within the same story or paragraph cluster as the correct answer" in prompt
        assert "Do not use unrelated skim items or different article topics as distractors" in prompt
        assert "If the answer is about FEST, every wrong option should be a plausible misunderstanding of FEST" in prompt
        assert "Keep all four options similar in length and specificity" in prompt
        assert "overclaiming rollout or adoption" in prompt
        assert "treating a workflow/pipeline as one smarter model" in prompt


def test_digest_quiz_prompt_anchors_options_to_one_body_section():
    for digest_type in ["research", "business"]:
        prompt = get_digest_quiz_prompt(digest_type, "en")

        assert "Silently choose one anchor section and one anchor paragraph" in prompt
        assert "All four options must be derived from that same anchor section" in prompt
        assert "Do not use names, products, projects, companies, methods, or claims that do not appear in the anchor section" in prompt
        assert "Do not use a different story as a distractor" in prompt
        assert "For beginner wrong options, do not introduce named entities, products, legal topics, regulatory topics, or tool names that are absent from the question and correct option" in prompt
        assert "If the question is anchored on a compute story, every wrong option must stay about compute access, cost, contracts, availability, or openness" in prompt


def test_digest_quiz_prompt_requires_single_task_and_option_length_balance():
    for digest_type in ["research", "business"]:
        prompt = get_digest_quiz_prompt(digest_type, "en")

        assert "Option Writing Contract" in prompt
        assert "Each quiz must ask exactly one task" in prompt
        assert "Do not ask \"what changed and why it matters\" in one question" in prompt
        assert "Before writing options, choose one option shape" in prompt
        assert "Options are answer choices, not mini-explanations" in prompt
        assert "The correct option must express one claim only" in prompt
        assert "The correct option must not be the only option with a caveat, condition, number, or named mechanism" in prompt
        assert "No option should be more than 30% longer than the median option length" in prompt
        assert "If one is, rewrite all four options before returning" in prompt


def test_digest_quiz_prompt_requires_short_parallel_option_shapes():
    for digest_type in ["research", "business"]:
        prompt = get_digest_quiz_prompt(digest_type, "en")

        assert "For mechanism questions, write each option as a short mechanism label plus the object it changes" in prompt
        assert "For limitation questions, write each option as one limitation label" in prompt
        assert "Do not make one option the only full sentence while the others are fragments" in prompt
        assert "Correct options should usually be 18 English words or fewer" in prompt
        assert "Korean options should usually fit in one short line" in prompt
        assert "English options must be 6-14 words and no more than 90 characters" in prompt
        assert "For research mechanism questions, prefer compact labels like" in prompt


def test_digest_quiz_prompt_separates_personas_without_making_expert_exam_like():
    prompt = get_digest_quiz_prompt("research", "en")

    assert "light end-of-article recap, not an exam" in prompt
    assert "expert: practical judgment check for working professionals" in prompt
    assert "answerable after reading the digest, not a technical exam" in prompt
    assert "Wrong options should be common overreactions or unsupported leaps, not obscure traps" in prompt
    assert "The three persona quizzes must test different reader tasks" in prompt
    assert "If two questions feel answerable by the same sentence from the digest, rewrite one of them" in prompt
    assert "learner tests causal understanding" in prompt
    assert "beginner tests misconception resistance" in prompt


def test_digest_quiz_prompt_requires_answers_recoverable_from_body():
    for digest_type in ["research", "business"]:
        prompt = get_digest_quiz_prompt(digest_type, "en")

        assert "Body Grounding" in prompt
        assert "Every correct answer must be directly grounded in a clear sentence or paragraph from that persona's digest body" in prompt
        assert "Do not ask the reader to infer a new action, strategy, or recommendation that is not stated in that persona's body" in prompt
        assert "the answer must be recoverable from the text the reader just read" in prompt
        assert 'Prefer "According to the digest"' in prompt


def test_digest_quiz_prompt_explains_only_the_selected_answer():
    for digest_type in ["research", "business"]:
        prompt = get_digest_quiz_prompt(digest_type, "en")

        assert "Explanation Contract" in prompt
        assert "Explain only why the selected answer is correct" in prompt
        assert "Do not explain why incorrect options are wrong" in prompt
        assert "Do not mention other options, distractors, or tempting wrong answers" in prompt
        assert "Do not write labels like Correct:, The correct answer, Option 2, Choice B" in prompt
        assert "If you mention a tempting wrong option" not in prompt


def test_digest_quiz_prompt_uses_digest_type_specific_focus():
    research_prompt = get_digest_quiz_prompt("research", "en")
    business_prompt = get_digest_quiz_prompt("business", "en")

    assert "Digest-Type Quiz Focus" in research_prompt
    assert "For research digests:" in research_prompt
    assert "Focus on what the method changed, what evidence supports it, and what the reported result does or does not prove." in research_prompt
    assert "Research learner: ask how the method works at a high level and why the result improved." in research_prompt
    assert "Avoid turning research questions into procurement, market strategy, or vendor-buying questions" in research_prompt
    assert "For business digests:" not in research_prompt

    assert "Digest-Type Quiz Focus" in business_prompt
    assert "For business digests:" in business_prompt
    assert "Focus on product, market, adoption, governance, data control, procurement, contracts, distribution, or operational risk." in business_prompt
    assert "Business expert: ask what a team should verify in buying, deploying, contracting, compliance, or risk management." in business_prompt
    assert "Avoid asking deep technical mechanism or benchmark-interpretation questions" in business_prompt
    assert "For research digests:" not in business_prompt


def test_digest_prompt_requires_quiz_answer_explanation_consistency():
    for digest_type in ["research", "business"]:
        prompt = get_digest_quiz_prompt(digest_type, "ko")

        assert "Korean quiz" in prompt
        assert "Do not use English prose except proper nouns" in prompt
        assert "Consistency Guard" in prompt
        assert "answer_index MUST point to the option your explanation treats as true" in prompt
        assert "explanation says \"not\"" in prompt
        assert "do not select an affirmative option that says the opposite" in prompt
        assert "Do not mention option positions in explanation" in prompt
        assert "Do not write labels like Option 2, Option 4, Choice B, first option, 정답(2), 정답은 첫 번째 옵션, 두 번째 옵션, 2번, or 첫 번째 선택지" in prompt


def test_learner_prompt_requires_plain_language_before_benchmarks():
    prompt = get_digest_prompt("research", "learner", [])

    assert "the first sentence after every `###` heading must explain" in prompt
    assert "before benchmarks, acronyms, or secondary details" in prompt
    assert "must stay fully grounded in the provided sources" in prompt


def test_learner_prompt_allows_compressing_secondary_detail_after_plain_language_opening():
    prompt = get_digest_prompt("research", "learner", [])

    assert "learner may compress secondary benchmark, architecture, or pricing detail" in prompt
    assert "after the plain-language opening" in prompt


def test_learner_prompt_requires_short_but_substantive_paragraphs():
    research_learner = get_digest_prompt("research", "learner", [])
    business_learner = get_digest_prompt("business", "learner", [])
    research_expert = get_digest_prompt("research", "expert", [])

    for prompt in [research_learner, business_learner]:
        assert "Compress by omitting lower-value secondary detail, not by shrinking every paragraph to one sentence." in prompt
        assert "Each learner item should cover this role sequence: what happened, why it matters, and what to watch or try." in prompt
        assert "For [LEAD], each paragraph should usually contain 2-3 sentences" in prompt
        assert "For [SUPPORTING], each paragraph should contain at least 2 sentences" in prompt

    assert "Compress by omitting lower-value secondary detail" not in research_expert
    assert "For [SUPPORTING], each paragraph should contain at least 2 sentences" not in research_expert


def test_learner_prompt_allows_shorter_supporting_items_than_expert():
    research_learner = get_digest_prompt("research", "learner", [])
    business_learner = get_digest_prompt("business", "learner", [])
    research_expert = get_digest_prompt("research", "expert", [])

    for prompt in [research_learner, business_learner]:
        assert "**[SUPPORTING] items**: 2-3 paragraphs" in prompt
        assert "Learner supporting items may stop at 2 paragraphs" in prompt

    assert "**[SUPPORTING] items**: every remaining item gets at least 3 paragraphs" in research_expert
    assert "Learner supporting items may stop at 2 paragraphs" not in research_expert


def test_learner_quality_rubrics_do_not_require_three_supporting_paragraphs():
    assert "supporting 2-3 paragraphs" in QUALITY_CHECK_RESEARCH_LEARNER
    assert "supporting stories may be 2-3 paragraphs" in QUALITY_CHECK_BUSINESS_LEARNER
    assert "supporting at least 3" not in QUALITY_CHECK_RESEARCH_LEARNER
    assert "supporting at least 3" not in QUALITY_CHECK_BUSINESS_LEARNER


def test_learner_quality_rubrics_flag_one_sentence_paragraph_chains():
    for prompt in [QUALITY_CHECK_RESEARCH_LEARNER, QUALITY_CHECK_BUSINESS_LEARNER]:
        assert "one-sentence learner paragraphs" in prompt
        assert "2+ sentences" in prompt
        assert "thin paragraph chain" in prompt


def test_beginner_quality_rubrics_cover_beginner_specific_failures():
    for prompt in [QUALITY_CHECK_RESEARCH_BEGINNER, QUALITY_CHECK_BUSINESS_BEGINNER]:
        assert "Beginner persona" in prompt
        assert "main_vs_skim" in prompt
        assert "one_line_scope" in prompt
        assert "schema_placeholder" in prompt
        assert "term_definition_repetition" in prompt
        assert "quiz_grounding" in prompt
        assert "quiz_distractor_scope" in prompt
        assert "quiz_answer_integrity" in prompt
        assert "quiz_beginner_fit" in prompt
        assert "학습자 뉴스 이어읽기" in prompt
        assert "보세요" in prompt
        assert "중점으로 보자" in prompt

    assert "one_line_jargon_density" in QUALITY_CHECK_RESEARCH_BEGINNER
    assert "new risk/check burden is exposed" in QUALITY_CHECK_RESEARCH_BEGINNER
    assert "research_burden_reduction" in QUALITY_CHECK_RESEARCH_BEGINNER
    assert "rollout_overclaim" in QUALITY_CHECK_BUSINESS_BEGINNER
    assert "business_lens_sentence" in QUALITY_CHECK_BUSINESS_BEGINNER
    assert "main_item_problem_first" in QUALITY_CHECK_RESEARCH_BEGINNER
    assert "main_item_term_budget" in QUALITY_CHECK_RESEARCH_BEGINNER
    assert "Count acronyms, benchmark names, vulnerability types" in QUALITY_CHECK_RESEARCH_BEGINNER
    assert "do not count company names, product names, source names" in QUALITY_CHECK_RESEARCH_BEGINNER
    assert "Extra terms may appear in paragraph 2" in QUALITY_CHECK_RESEARCH_BEGINNER
    assert "main_item_problem_first" in QUALITY_CHECK_BUSINESS_BEGINNER
    assert "main_item_term_budget" in QUALITY_CHECK_BUSINESS_BEGINNER
    assert "Count acronyms, benchmark names, vulnerability types" in QUALITY_CHECK_BUSINESS_BEGINNER
    assert "do not count company names, product names, source names" in QUALITY_CHECK_BUSINESS_BEGINNER
    assert "Extra terms may appear in paragraph 2" in QUALITY_CHECK_BUSINESS_BEGINNER


def test_learner_quality_rubrics_penalize_high_risk_ko_literal_translations_without_schema_change():
    for prompt in [QUALITY_CHECK_RESEARCH_LEARNER, QUALITY_CHECK_BUSINESS_LEARNER]:
        assert "literal translation Korean" in prompt
        assert "dictionary-like translations" in prompt
        assert "deployment → not always `배치`" in prompt
        assert "entity → not `법인` unless legal corporation is meant" in prompt
        assert "agent → not `대리인` in AI product contexts" in prompt
        assert '"fluency":' in prompt
        assert '"literal_translation"' not in prompt


def test_business_prompt_keeps_strategy_sections():
    prompt = get_digest_prompt("business", "expert", [])

    assert "## Connecting the Dots" in prompt
    assert "## Strategic Decisions" in prompt


def test_business_expert_prompt_distinguishes_fact_from_inference():
    prompt = get_digest_prompt("business", "expert", [])

    assert "State sourced facts directly." in prompt
    assert "use calibrated language such as" in prompt
    assert "signals, points to, implies, or suggests" in prompt


def test_business_expert_prompt_separates_front_load_from_analysis_sections():
    prompt = get_digest_prompt("business", "expert", [])

    assert "In the headline, excerpt, and first paragraph of each item, lead with sourced facts and only light interpretation." in prompt
    assert "Stronger synthesis belongs in sections like Connecting the Dots and Strategic Decisions." in prompt
    assert "If a claim depends mainly on secondary reporting, keep it out of the headline and excerpt" in prompt


def test_business_expert_prompt_softens_secondary_source_interpretation_in_front_load():
    prompt = get_digest_prompt("business", "expert", [])

    assert 'avoid definitive competitive verbs such as "hits", "undercuts", "wins", "replaces", or "reduces reliance on"' in prompt
    assert 'phrase it with softer language such as "signals", "suggests", "raises pressure on", or "is positioned as"' in prompt


def test_business_prompt_uses_source_metadata_for_front_load_calibration():
    prompt = get_digest_prompt("business", "expert", [])

    assert "PRIMARY sources can support direct factual statements in the headline, excerpt, and first paragraph." in prompt
    assert "SECONDARY or analysis sources should be framed more cautiously in those front-loaded positions." in prompt
    assert "Treat official_platform_asset sources as factual for release details, but keep strategic interpretation one step more cautious than official_site or paper sources." in prompt


def test_business_prompt_makes_front_load_observable_event_first_for_secondary_sources():
    prompt = get_digest_prompt("business", "expert", [])

    assert "If a lead story is supported mostly by SECONDARY, analysis, or official_platform_asset sources, anchor the headline, excerpt, and first paragraph to the observable event first before any market interpretation." in prompt
    assert 'Prefer factual front-load verbs such as "launches", "releases", "announces", "files", "opens", "reviews", "says", or "prices" over dramatic framing.' in prompt
    assert 'Avoid loaded words such as "scramble", "showdown", "takes aim", "shot at", "salvo", or "war" in the headline, excerpt, and first paragraph unless the source itself uses that framing.' in prompt


def test_business_prompts_require_attribution_and_dates_for_secondary_only_metrics():
    expert_prompt = get_digest_prompt("business", "expert", [])
    learner_prompt = get_digest_prompt("business", "learner", [])
    research_prompt = get_digest_prompt("research", "expert", [])

    for prompt in [expert_prompt, learner_prompt]:
        assert "Secondary-only metrics" in prompt
        assert "reported by <source>" in prompt
        assert "as of <absolute date>" in prompt
        assert "live rankings, token counts, app-store ranks, leaderboard positions" in prompt
        assert "Do not put secondary-only strategic conclusions in headline/excerpt" in prompt

    assert "Secondary-only metrics" not in research_prompt


def test_business_prompts_soften_product_launch_claims_when_only_secondary_sources_are_available():
    expert_prompt = get_digest_prompt("business", "expert", [])
    learner_prompt = get_digest_prompt("business", "learner", [])

    for prompt in [expert_prompt, learner_prompt]:
        assert "If no official or PRIMARY source is available for a product launch" in prompt
        assert "attribute company claims to the reporting source" in prompt
        assert "avoid writing `OpenAI says` or `Google says`" in prompt
        assert "Do not infer procurement speed, pilot readiness, or production deployment" in prompt
        assert "scope an inquiry" in prompt


def test_quality_rubrics_penalize_secondary_only_metrics_without_attribution_or_dates():
    assert "secondary-only metric or strategic conclusion in headline/excerpt without attribution" in QUALITY_CHECK_FRONTLOAD
    assert "live metric without an as-of date" in QUALITY_CHECK_FRONTLOAD

    for prompt in [QUALITY_CHECK_BUSINESS_EXPERT, QUALITY_CHECK_BUSINESS_LEARNER]:
        assert "Single-secondary-source metrics" in prompt
        assert "live rankings, token counts, app-store ranks, leaderboard positions" in prompt
        assert "must be attributed and tied to an absolute as-of date" in prompt
        assert '"secondary_source_calibration"' not in prompt


def test_quality_rubrics_allow_secondary_only_when_primary_source_is_absent():
    source_quality_prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_WEEKLY_EXPERT,
        QUALITY_CHECK_WEEKLY_LEARNER,
    ]
    for prompt in source_quality_prompts:
        assert "Secondary-only stories are allowed when the source set lacks a primary/official source" in prompt
        assert "do NOT penalize source_quality solely because no official source exists" in prompt
        assert "Penalize primary_source_priority only when a primary/official source is present" in prompt

    calibration_prompts = [
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
        QUALITY_CHECK_FRONTLOAD,
    ]
    for prompt in calibration_prompts:
        assert "evaluate attribution and calibration instead" in prompt
        assert "avoid definitive company-claim phrasing unless an official source is available" in prompt


def test_research_prompt_has_license_sensitive_wording_guard():
    prompt = get_digest_prompt("research", "expert", [])

    assert 'do NOT call it "open-source" or "open source"' in prompt
    assert 'Use "public weights", "weights released", or "released under non-commercial terms" instead.' in prompt


def test_digest_prompt_requires_english_field_purity():
    prompt = get_digest_prompt("research", "expert", [])

    assert "EN FIELD PURITY" in prompt
    assert "The `en` field is a standalone English article." in prompt
    assert "Do not use Hangul anywhere in the English headline, excerpt, section summaries, `###` headings, or body paragraphs." in prompt


def test_digest_prompt_requires_english_only_subheadings_and_checklist():
    prompt = get_digest_prompt("research", "expert", [])

    assert "**EN `###` headings**: MUST be English-only." in prompt
    assert "### ClawBench: Agent performance on everyday web tasks" in prompt
    assert "Does the `en` field contain any Hangul in the headline, excerpt, `###` headings, or body?" in prompt


def test_en_heading_has_three_transformation_rules():
    """Apr 24 regression: Business Expert pasted source article titles verbatim
    (publisher suffix `- TechCrunch`, 147-char press-release sprawl, Title Case).
    Prompt must show all three failure modes as bad/good contrastive examples
    (per prompt-engineering-patterns 'Show, Don't Tell')."""
    prompt = get_digest_prompt("business", "expert", [])

    # Rule 1: publisher suffix stripping — concrete transformation shown
    assert "Sierra acquires YC-backed Fragment to expand agent development" in prompt
    assert "Strip publisher suffix" in prompt
    # Rule 2: press-release sprawl compression
    assert "Press-release sprawl" in prompt or "press-release sprawl" in prompt
    assert "Resolve AI raises $40M at $1.5B" in prompt
    # Rule 3: Title Case → sentence case
    assert "Editorial voice, not Title Case" in prompt
    # Checklist has the 3-failure-mode scan
    assert "Publisher suffix present" in prompt
    assert "press release" in prompt.lower()
    assert "Title Case" in prompt


def test_classification_prompt_allows_cross_category_overlap_for_dual_significance():
    assert "The same article CAN appear in both categories if relevant to both" in CLASSIFICATION_SYSTEM_PROMPT
    assert "The same article CAN and SHOULD appear in both categories when it has both technical and business significance." in CLASSIFICATION_SYSTEM_PROMPT
    assert "overlap is valuable, not redundant." in CLASSIFICATION_SYSTEM_PROMPT


def test_digest_prompt_reframes_one_line_summary_as_top_story_synthesis():
    prompt = get_digest_prompt("business", "expert", [])

    assert "should synthesize the common pattern across the top 2-3 stories in one sentence." in prompt
    assert "It should not read like a stitched list of headlines." in prompt
    assert "Name the shift, pressure, or pattern that connects the stories." in prompt
    assert "15 English words" not in prompt
    assert "60 Korean chars" not in prompt


def test_learner_prompt_prefers_news_editor_tone_over_chatty_friend_tone():
    prompt = get_digest_prompt("research", "learner", [])

    assert "written news/editorial prose" in prompt
    assert "knowledgeable friend explaining over lunch" not in prompt
    assert "Write the learner version in clear editorial news prose" in prompt
    assert 'Do not write body paragraphs in a friendly spoken "~요" tone.' in prompt


def test_learner_prompt_guides_high_risk_ko_literal_translations():
    research_prompt = get_digest_prompt("research", "learner", [])
    business_prompt = get_digest_prompt("business", "learner", [])
    expert_prompt = get_digest_prompt("business", "expert", [])

    for prompt in [research_prompt, business_prompt]:
        assert "High-risk literal translations" in prompt
        assert "deployment" in prompt
        assert "do not default to `배치`" in prompt
        assert "entity" in prompt
        assert "do not use `법인` unless the source means a legal corporation" in prompt
        assert "agent" in prompt
        assert "do not translate as `대리인`" in prompt

    assert "High-risk literal translations" not in expert_prompt


def test_business_expert_prompt_uses_editorial_brief_tone_not_private_advisor_tone():
    prompt = get_digest_prompt("business", "expert", [])

    assert "strategic news brief" in prompt
    assert "trusted strategic advisor in a private briefing" not in prompt
    assert "foreground the concrete market-moving event or decision first" in prompt
    assert "Avoid semicolon headlines or stitched three-story rollups" in prompt


def test_expert_title_strategy_prefers_one_clear_throughline_over_glued_lists():
    prompt = get_digest_prompt("research", "expert", [])

    assert "The frontload should make today's main shift legible quickly" in prompt
    assert "Do not pack too many separate stories into one line." in prompt
    assert "Prefer one clear throughline over a list of 2-3 headlines glued together." in prompt
    assert "Move technical knobs, benchmark details, and specialist phrasing into the body" in prompt


def test_learner_title_strategy_says_what_changed_before_the_mechanism():
    prompt = get_digest_prompt("research", "learner", [])

    assert "Say what changed before naming the technical mechanism." in prompt
    assert "Prefer user-visible or decision-relevant impact before jargon." in prompt
    assert "If a technical term appears, it should not be the first thing the reader has to decode." in prompt


def test_research_prompts_frontload_practical_advance_before_shorthand():
    expert_prompt = get_digest_prompt("research", "expert", [])
    learner_prompt = get_digest_prompt("research", "learner", [])

    for prompt in [expert_prompt, learner_prompt]:
        assert "foreground the practical advance before the technical mechanism." in prompt
        assert "Avoid leading with insider shorthand such as FP8, KV cache, policy routing" in prompt


def test_quality_prompts_allow_brief_uncited_one_line_summary():
    prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
    ]

    for prompt in prompts:
        # Rubric v2 (NP-QUALITY-06): phrase kept inline in sub-score descriptions
        # Accept either full form "may be brief if it synthesizes" or short form
        # "may be brief if synthetic" depending on persona.
        assert "One-Line Summary may be brief" in prompt


def test_quality_prompts_require_structured_issue_schema():
    prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
    ]

    for prompt in prompts:
        assert '"severity": "major|minor"' in prompt
        # Rubric v2: scope is per-persona subset (expert_body|ko|en or learner_body|ko|en).
        # Require ko + en at minimum, plus one of expert_body / learner_body.
        assert '"scope":' in prompt
        assert "ko|en" in prompt
        assert ("expert_body" in prompt) or ("learner_body" in prompt)
        assert '"category":' in prompt
        # Category enum varies by persona but must include at least source + locale + structure
        for required_category in ("source", "locale", "structure"):
            assert required_category in prompt


def test_digest_writer_prompt_enforces_frontload_locale_parity():
    """Writer prompt must forbid KO frontload from adding facts not in EN.

    Dominant failure mode in 4/8-4/14 rescore was KO headline/excerpt
    adding numbers, rankings, or allegations not present in EN. This
    rule is prevention for that pattern — the code-level penalty check
    (if added later) is detection.
    """
    for digest_type, persona in [
        ("research", "expert"),
        ("research", "learner"),
        ("business", "expert"),
        ("business", "learner"),
    ]:
        prompt = get_digest_prompt(digest_type, persona, [])
        assert "Frontload Locale Parity" in prompt
        # Core rule
        assert "NATURAL TRANSLATIONS" in prompt
        assert "translation, not a rewrite" in prompt or "translation, not" in prompt.lower()
        # Explicit DO NOT list
        assert "DO NOT add to KO" in prompt
        assert "DO NOT omit from KO" in prompt
        # Checklist item
        assert "Frontload locale parity" in prompt


def test_quality_prompts_include_severity_rubric_and_scoring_resolution():
    """Severity taxonomy + scoring resolution guidance must be present.

    Without these, LLM judges drift: severity gets applied subjectively and
    body scores saturate at 95-100. Regression guard against accidental
    removal during future prompt edits.

    NQ-37 (2026-04-21): frontload migrated to v11 format, so it's now tested
    alongside the 4 body prompts on the shared rubric contract. The only
    difference is frontload has no `locale_integrity` sub-dimension (that's
    a body-specific check); frontload uses `fact_parity`/`entity_parity`
    /`phrase_naturalness` for its locale_alignment category instead.
    """
    from services.agents.prompts_news_pipeline import QUALITY_CHECK_FRONTLOAD

    v11_prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
        QUALITY_CHECK_FRONTLOAD,
    ]

    for prompt in v11_prompts:
        # Severity rubric (header + fabrication + locale corruption + hard cap)
        assert "## Severity" in prompt
        assert "fabrication" in prompt.lower()
        assert "locale corruption" in prompt.lower()  # NP-QUALITY-06: explicit locale check
        assert "When unsure" in prompt or "minor" in prompt.lower()  # tiebreaker
        assert "≤3 issues" in prompt or "AT MOST 3" in prompt  # hard cap
        assert "Zero is valid" in prompt or "ZERO issues" in prompt  # anti-invention
        # Rubric v2: 0-10 scale anchors (replaces old 0-25 calibration tier anchors)
        assert "Scoring Scale" in prompt
        assert "Exemplary" in prompt  # 10 anchor
        assert "Solid" in prompt      # 7 anchor
        assert "Weak" in prompt       # 4 anchor
        # Evidence requirement (prevents LLM hedging without grounding)
        assert "evidence" in prompt.lower()
        assert "score" in prompt.lower()
        # v11 rubric: no single-number total (code aggregates)
        assert "no total score" in prompt.lower() or "code aggregates" in prompt.lower()

    # Body-specific: locale_integrity sub-dimension (NP-QUALITY-06 key addition)
    for body in v11_prompts[:4]:
        assert "locale_integrity" in body


def test_frontload_prompt_has_v11_ten_subscores():
    """NQ-37: frontload QC v11 format — 10 sub-scores grouped into 4 categories
    (factuality, calibration, clarity, locale_alignment), with evidence required
    per sub-score and no LLM-emitted total.
    """
    from services.agents.prompts_news_pipeline import QUALITY_CHECK_FRONTLOAD

    # 4 category headings
    assert "### Factuality" in QUALITY_CHECK_FRONTLOAD
    assert "### Calibration" in QUALITY_CHECK_FRONTLOAD
    assert "### Clarity" in QUALITY_CHECK_FRONTLOAD
    assert "### Locale Alignment" in QUALITY_CHECK_FRONTLOAD

    # 10 sub-score keys (body ↔ label text AND JSON output schema)
    sub_keys = [
        "number_grounding", "entity_grounding", "claim_grounding",           # factuality (3)
        "claim_strength", "framing_calibration",                             # calibration (2)
        "headline_specificity", "focus_items_informativeness",               # clarity (2)
        "fact_parity", "entity_parity", "phrase_naturalness",                # locale_alignment (3)
    ]
    for k in sub_keys:
        assert k in QUALITY_CHECK_FRONTLOAD, f"missing sub-score key: {k}"

    # Old single-score contract must be gone
    assert '"score": 0-100' not in QUALITY_CHECK_FRONTLOAD
    assert '"subscores"' not in QUALITY_CHECK_FRONTLOAD  # old flat subscores block

    # Forward-looking verb guard surfaces in calibration dimension (aligns with writer guard)
    assert "forward-looking" in QUALITY_CHECK_FRONTLOAD.lower() or "Expect X to Y" in QUALITY_CHECK_FRONTLOAD


def test_learner_title_strategy_keeps_ko_body_editorial_not_conversational():
    prompt = get_digest_prompt("business", "learner", [])

    assert "Use readable editorial news prose, not chatty spoken copy." in prompt
    assert "News sections should default to concise editorial 기사체." in prompt
    assert "친근체 (-에요/-습니다), unchanged." not in prompt


def test_locale_integrity_exempts_cp_attribution_lines():
    """Apr 22 bug: CP post-processor adds `> — [Hacker News](URL)` attribution lines
    after quotes. These are `>` blockquote lines with no Hangul, triggering false
    MAJOR locale_integrity violations. Rubric must explicitly exempt them.
    All 4 daily body prompts + 2 weekly prompts (6 total) share the locale check."""
    v11_prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
    ]
    for prompt in v11_prompts:
        # Must mention the exemption for attribution lines
        assert "EXEMPT" in prompt
        assert "attribution lines" in prompt
        # Must reference the two attribution formats that CP post-processing produces
        assert "> — <Label>" in prompt or "> — [<Label>]" in prompt


def test_locale_integrity_anchors_scope_to_ko_body_marker():
    """Apr 22 regression (2nd kind): judge confused EN body English blockquotes
    as KO locale violations. Rubric must explicitly tell the judge to scan
    ONLY the `=== KO BODY ===` section — Apr 22 rerun showed the judge
    quoting EN body content in a 'KO locale violation' report.
    The scope anchor aligns with _build_body_quality_payload's explicit
    section labels."""
    v11_prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
    ]
    for prompt in v11_prompts:
        # Scope anchor — must tell judge to scan ONLY below the KO BODY marker
        assert "=== KO BODY ===" in prompt
        # EN body English quotes must be explicitly marked as acceptable
        assert "=== EN BODY ===" in prompt
        assert "MUST be ignored" in prompt or "ignore" in prompt.lower()
        # Self-verify clause — judge must confirm evidence is a substring of KO
        # BODY before reporting. Apr 22 rerun: even with scope anchor alone,
        # judge hallucinated EN quotes as KO violations. Self-verify forces
        # the judge to find the text in KO BODY literally or score 10.
        assert "SELF-VERIFY" in prompt
        assert "substring" in prompt
        assert "score 10" in prompt or "is NOT a violation" in prompt


def test_locale_integrity_keeps_cp_body_in_scope():
    """2026-04-24: narrowed the CP exemption after external review flagged
    it as single-layer defense. Attribution lines stay exempt (they're
    CP-post-processor citation markers with no Korean body content), but
    Community Pulse blockquote bodies + prose paragraphs stay subject to
    the Hangul rule — code retranslation is the primary defense, rubric
    is the secondary catch. Apr 19 incident is the canonical failure mode
    this guards against."""
    v11_prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
    ]
    for prompt in v11_prompts:
        # CP section body must be NOT exempt — old "ALSO EXEMPT: all content
        # inside ## 커뮤니티 반응" clause has been removed.
        assert "ALSO EXEMPT" not in prompt
        assert "NOT EXEMPT" in prompt
        assert "커뮤니티 반응" in prompt
        assert "Community Pulse" in prompt
        # Attribution-only exemption must remain
        assert "attribution lines" in prompt
        # Reason must be stated so judge understands why to skip
        assert "code-validated" in prompt or "_has_hangul" in prompt or "summarize_community" in prompt


def test_locale_integrity_allows_mixed_proper_noun_ko_headings():
    """May 19 regression: research paper titles in Latin script can appear in
    KO `###` headings when followed by Korean explanation. That is not
    English leakage; only English-only KO prose/blockquotes should trigger a
    major locale issue and cap the score."""
    prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
        QUALITY_CHECK_RESEARCH_BEGINNER,
        QUALITY_CHECK_BUSINESS_BEGINNER,
    ]
    for prompt in prompts:
        assert "Mixed proper-noun headings are allowed" in prompt
        assert "<English proper title>: <Korean explanation>" in prompt
        assert "Known By Their Actions: 웹 브라우저 에이전트 행동 지문 식별" in prompt
        assert "English-only paragraph" in prompt
        assert "English-only `>` blockquote" in prompt
        assert "Do NOT create a major locale issue" in prompt


def test_locale_integrity_allows_canonical_english_section_headings():
    """Canonical navigation labels stay English by editorial choice, even in KO."""
    prompts = [
        QUALITY_CHECK_RESEARCH_EXPERT,
        QUALITY_CHECK_RESEARCH_LEARNER,
        QUALITY_CHECK_BUSINESS_EXPERT,
        QUALITY_CHECK_BUSINESS_LEARNER,
        QUALITY_CHECK_RESEARCH_BEGINNER,
        QUALITY_CHECK_BUSINESS_BEGINNER,
        QUALITY_CHECK_WEEKLY_EXPERT,
        QUALITY_CHECK_WEEKLY_LEARNER,
    ]
    for prompt in prompts:
        assert "Canonical English section headings are an editorial convention" in prompt
        assert "`## Research Papers`" in prompt
        assert "`## Open Source & Repos`" in prompt
        assert "`## Big Tech`" in prompt
        assert "`## Industry & Biz`" in prompt
        assert "`## New Tools`" in prompt
        assert "do NOT treat these section headings as locale violations" in prompt


def test_business_expert_strategic_decisions_requires_citations():
    """Apr 22 bug: Business expert Strategic Decisions section shipped 5 bullets
    with 0 citations — strategic guidance without sources reads as editorial.
    Writer prompt must explicitly require a citation placeholder on every bullet."""
    prompt = get_digest_prompt("business", "expert", [])

    assert "## Strategic Decisions" in prompt
    # Format line must now include `[CITE_N]` at end (Apr 23 migration)
    assert "[consequence] [CITE_N]" in prompt
    # Explicit rule about citing
    assert "Every bullet MUST end with `[CITE_N]`" in prompt
    # Example must demonstrate a citation at the end
    assert "https://openai.com/blog" in prompt  # example URL in the citations[] sample


def test_hallucination_guard_enforces_attribution_url_domain_match():
    """Apr 22 bug: 'Associated Press reports [4](https://www.mrt.com/...)' —
    attribution named AP but URL points to a local paper (mrt.com) that syndicates
    AP content. HALLUCINATION_GUARD must require attribution phrase to match URL
    domain. Applies to every daily + weekly writer prompt."""
    prompt = get_digest_prompt("business", "expert", [])

    assert "Attribution must match URL domain" in prompt
    # Mention of syndication handling
    assert "syndicat" in prompt.lower()
    # The wire services that commonly trigger this (examples in the rule)
    assert "Reuters" in prompt or "AP" in prompt or "Associated Press" in prompt


def test_focus_items_p2_bullet_forbids_evaluative_phrasing():
    """Apr 22 bug: focus_items bullet 2 used 'Raises bar for creative and marketing
    workflows' — evaluative, press-release tone. Writer prompt must give explicit
    guidance for bullet 2 to use objective mechanism/consequence phrasing instead
    of evaluative verbs."""
    prompt = get_digest_prompt("business", "expert", [])

    # Explicit forbidden verbs + preferred alternatives
    assert "raises bar" in prompt.lower()
    assert "transforms" in prompt.lower()
    # Preferred alternatives shown
    assert "enables X" in prompt or "enables " in prompt
    # P2 role must be clarified as objective consequence, not evaluation
    assert "objective consequence" in prompt or "not evaluation" in prompt.lower() or "not prediction" in prompt.lower()
