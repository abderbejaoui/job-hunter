"""The fit score: what it measures, and what it refuses to be fooled by.

The property under test throughout is the one that makes measuring twice worth
anything: evidence is looked up in the profile, so tailoring can move what is
*shown* and can never move what is *evidenced*.
"""

import jobhunt
import pytest
from jobhunt import (
    EVIDENCED,
    NOT_CHECKABLE,
    NOT_EVIDENCED,
    Job,
    Profile,
    Role,
)

JOB = Job(
    title="Senior Data Engineer", company="Zeta", url="https://zeta.example/j/1",
    requirements=[
        "Deep PostgreSQL knowledge",
        "Experience with dbt",
        "Experience running OpenStack in production",
        "Strong communication skills",
    ],
    nice_to_have=["Airflow"],
)


def test_evidence_comes_from_the_profile(profile):
    found = jobhunt.score(JOB, profile)
    backed = {r.text: r.status for r in found.required}
    assert backed["Experience with dbt"] == EVIDENCED
    assert backed["Experience running OpenStack in production"] == NOT_EVIDENCED


def test_a_requirement_with_nothing_concrete_is_not_counted(profile):
    found = jobhunt.score(JOB, profile)
    soft = next(r for r in found.required if "communication" in r.text)
    assert soft.status == NOT_CHECKABLE
    assert soft.why
    assert soft not in found.checkable


def test_the_evidence_is_quoted_so_it_can_be_checked(profile):
    found = jobhunt.score(JOB, profile)
    dbt = next(r for r in found.required if "dbt" in r.text)
    assert dbt.evidence[0].where.startswith("experience[")
    assert "dbt" in dbt.evidence[0].quote


# --- the one this package exists for ----------------------------------------

def test_parroting_the_posting_earns_nothing(profile, job):
    """A CV that copies the job's words must not score better for it."""
    before = jobhunt.score(JOB, profile)

    parroted = jobhunt.tailor(profile, JOB, {
        "summary": " ".join(JOB.requirements),   # every requirement, verbatim
        "roles": [{"index": 0}], "projects": [], "skills": [],
    })
    after = jobhunt.score(JOB, profile, parroted, when="after")

    assert after.evidenced == before.evidenced, "tailoring cannot create evidence"
    assert "OpenStack" in after.parroting, "and the attempt is reported"


def test_the_job_is_never_treated_as_support(profile):
    """A posting asking for Kafka does not license claiming it."""
    asks_for_kafka = jobhunt.clone(JOB, **{"requirements": ["Experience with Kafka"],
                                            "keywords": ["Kafka"]})
    found = jobhunt.score(asks_for_kafka, profile)
    assert found.required[0].status == NOT_EVIDENCED


def test_evidenced_is_identical_before_and_after(profile):
    before = jobhunt.score(JOB, profile)
    tailored = jobhunt.tailor(profile, JOB, {"summary": "Data engineer.",
                                          "roles": [{"index": 0}], "projects": [],
                                          "skills": ["dbt"]})
    after = jobhunt.score(JOB, profile, tailored, when="after")
    assert before.evidenced == after.evidenced


# --- the skim window --------------------------------------------------------

#: Airflow sits only on one role's skills list in the fixture, which makes it
#: the clean probe: dbt is also a certification and a top-level skill, so it is
#: shown however the document is cut.
AIRFLOW = jobhunt.clone(JOB, **{"requirements": ["Experience with Airflow"],
                                 "nice_to_have": []})


def test_evidence_buried_deep_is_not_shown(profile):
    buried = jobhunt.clone(profile)
    buried.skills = []
    buried.experience[0].skills = []
    buried.experience[0].bullets = ["Did a thing."] * 20 + ["Ran the Airflow DAGs."]
    found = jobhunt.score(AIRFLOW, profile, buried, skim_bullets=5)
    airflow = found.required[0]
    assert airflow.present_anywhere and not airflow.shown_in_skim


def test_lifting_it_into_the_summary_shows_it(profile):
    lifted = jobhunt.clone(profile)
    lifted.skills = []
    lifted.experience = []
    lifted.summary = "Data engineer who ran the Airflow DAGs."
    found = jobhunt.score(AIRFLOW, profile, lifted, skim_bullets=0)
    assert found.required[0].shown_in_skim


def test_the_skills_list_is_below_the_fold(profile):
    """Every renderer puts Skills after Experience, Projects and Education. A
    term that lives only in the skills list is on the page but not in the
    first screenful - and counting it meant tailoring could never be seen to
    buy anything for anyone who lists their tools. SQL is only in the fixture's
    skills list; lifting it into the summary is what shows it."""
    sql = Job(title="Engineer", requirements=["Strong SQL"])
    before = jobhunt.score(sql, profile)
    assert before.required[0].present_anywhere
    assert not before.required[0].shown_in_skim
    lifted = jobhunt.tailor(profile, sql, {"summary": "Data engineer who writes the SQL.",
                                           "roles": [{"index": 0}], "projects": [],
                                           "skills": []})
    after = jobhunt.score(sql, profile, lifted, when="after")
    assert after.required[0].shown_in_skim
    assert after.shown == before.shown + 1
    assert after.evidenced == before.evidenced


def test_the_skim_is_every_title_and_no_projects(profile):
    """What fit's SKILL.md tells the agent the first screenful is. The bullet
    budget caps bullets only; projects print after Experience."""
    document = jobhunt.clone(profile)
    document.projects = [jobhunt.Project(name="Streamer", tech=["Kafka"])]
    skim = jobhunt._skim(document, 0)
    assert "Data Engineer Acme" in skim and "Analyst Beta" in skim
    assert "Cut ETL" not in skim
    assert "Kafka" not in skim


def test_dropping_evidence_entirely_is_a_regression(profile):
    stripped = jobhunt.clone(profile)
    stripped.experience = []
    stripped.skills = []
    found = jobhunt.score(AIRFLOW, profile, stripped, when="after")
    assert "Airflow" in found.regressions


# --- years ------------------------------------------------------------------

@pytest.mark.parametrize("line, expected", [
    ("3+ years of experience", 3),
    ("Five or more years building services", 5),
    ("Du hast etwa 4 Jahre Berufserfahrung", 4),
    ("au moins 3 ans", 3),
    ("A lot of experience", None),
])
def test_years_asked_for_is_read_when_it_is_legible(line, expected):
    assert jobhunt.years_required(line) == expected


def test_overlapping_roles_are_counted_once():
    doubled = Profile(experience=[
        Role(position="A", company="X", start="2020", end="2024"),
        Role(position="B", company="Y", start="2021", end="2023"),
    ])
    assert jobhunt.years_held(doubled) == 4


def test_months_count_for_what_they_are():
    """Two short roles in one year used to add up to zero: year arithmetic
    gave April to August nothing. They are a third of a year."""
    short = Profile(experience=[Role(position="A", company="X", start="2025-04", end="2025-08"),
                                Role(position="B", company="Y", start="2025-02", end="2025-04")])
    assert abs(jobhunt.years_held(short) - 0.5) < 0.01


def test_undated_roles_are_not_a_short_career():
    undated = Profile(experience=[Role(position="A", company="X", start="recently")])
    assert jobhunt.years_held(undated) is None


def test_the_years_gap_is_named_when_it_is_real(profile):
    demanding = jobhunt.clone(JOB, **{"requirements": ["10+ years with dbt"]})
    assert "tailoring cannot close" in jobhunt.score(demanding, profile).years_note


# --- shape ------------------------------------------------------------------

def test_a_posting_with_no_requirements_falls_back_to_keywords(profile):
    prose = Job(title="Data Engineer", company="Zeta",
                description="We need someone good.", keywords=["dbt", "OpenStack"])
    found = jobhunt.score(prose, profile)
    assert found.basis == "keywords"
    assert len(found.required) == 2


def test_nice_to_haves_are_counted_apart(profile):
    found = jobhunt.score(JOB, profile)
    assert [r.text for r in found.nice_to_have] == ["Airflow"]
    assert all(r.kind == "required" for r in found.checkable)


def test_the_same_inputs_give_the_same_report(profile):
    """A number that moves on its own is not worth printing."""
    first = jobhunt.score(JOB, profile)
    second = jobhunt.score(JOB, profile)
    assert first == second


def test_the_delta_reads_as_a_sentence(profile):
    before = jobhunt.score(JOB, profile)
    after = jobhunt.score(JOB, profile, when="after")
    written = jobhunt.delta(before, after)
    assert "unchanged by tailoring" in written
    assert "OpenStack" in written


@pytest.mark.parametrize("line, expected", [
    # A verb that opens a sentence is capitalised for being first.
    ("Build data pipelines in Python", ["Python"]),
    ("Own the ingestion pipelines", []),
    ("Design and implement REST APIs", ["REST", "APIs"]),
    ("Mentor junior engineers", []),
    ("Build REST APIs", ["REST", "APIs"]),
    # A tool that opens a line is the thing asked for, however the sentence
    # goes on - which is why the openers are a list and not a rule about
    # first words.
    ("Linux administration", ["Linux"]),
    ("Go services at scale", ["Go"]),
    ("Figma for design", ["Figma"]),
    ("Terraform to manage infrastructure", ["Terraform"]),
    ("React for building UIs", ["React", "UIs"]),
    ("Kubernetes for container orchestration", ["Kubernetes"]),
    ("Swift for iOS apps", ["Swift", "iOS"]),
    ("Terraform experience", ["Terraform"]),
    ("AWS certification preferred", ["AWS"]),
    ("CI/CD pipelines", ["CI/CD"]),
    ("Docker, Kubernetes, Helm", ["Docker", "Kubernetes", "Helm"]),
    ("Kubernetes and Docker", ["Kubernetes", "Docker"]),
    ("Kafka, Flink, or similar streaming technologies", ["Kafka", "Flink"]),
    ("Kafka", ["Kafka"]),
    ("Kubernetes in production", ["Kubernetes"]),
    ("Python (advanced)", ["Python"]),
    ("Deep PostgreSQL knowledge", ["PostgreSQL"]),
])
def test_a_verb_that_opens_a_line_is_not_a_name(line, expected):
    """"Build data pipelines" used to report a gap called Build, and "Own",
    "Design" and "Mentor" beside it - one per responsibility-shaped line."""
    assert jobhunt.salient_terms(line) == expected


@pytest.mark.parametrize("line, vocabulary, expected", [
    # Every word capitalised, the ordinary ones too: the capitals say nothing,
    # and only a name marked some other way counts.
    ("Excellent Problem Solving Skills", set(), []),
    ("Experience With PostgreSQL And AWS", set(), ["PostgreSQL", "AWS"]),
    # The cost, pinned so it is a decision and not a surprise.
    ("Strong Python Skills", set(), []),
    ("Strong Python Skills", {"python"}, ["Python"]),
    # A list of names capitalises no ordinary word, so it is not title case.
    ("Google Cloud Platform", set(), ["Google", "Cloud", "Platform"]),
    # A designer who lists Design is asked about it, opener or not.
    ("Design systems for mobile", {"design"}, ["Design"]),
])
def test_title_case_carries_no_signal(line, vocabulary, expected):
    assert jobhunt.salient_terms(line, frozenset(vocabulary)) == expected


@pytest.mark.parametrize("line, expected", [
    # Found on a live posting: two lowercase words joined by a slash are
    # not a tool, and were each reported as a gap.
    ("Understanding of distributed systems (networking, caching/storage concepts)", []),
    ("Comfortable writing docs/runbooks and collaborating across teams", []),
    ("Experience with service mesh patterns (e.g., Istio mTLS)", ["Istio", "mTLS"]),
    # A slash between acronyms joins them; anywhere else the parts are names
    # or not on their own.
    ("CI/CD and TCP/IP experience", ["CI/CD", "TCP/IP"]),
    ("Build REST/gRPC APIs", ["REST", "gRPC", "APIs"]),
    ("Node.js, .NET or C#", ["Node.js", "NET", "C#"]),
    # A hyphen is part of the name.
    ("Objective-C or Swift", ["Objective-C", "Swift"]),
])
def test_a_slash_between_two_words_is_punctuation_not_a_name(line, expected):
    assert jobhunt.salient_terms(line) == expected


def test_a_hyphenated_tool_the_candidate_lists_is_kept_whole():
    assert jobhunt.salient_terms("Experience with scikit-learn",
                                 frozenset({"scikit-learn"})) == ["scikit-learn"]


@pytest.mark.parametrize("line, expected", [
    # All found on live internship postings, run against a real CV. Each of
    # the capitalised words below was reported as a gap.
    ("Available for a Summer 2027 internship (May/June start dates)", []),
    ("Available to complete a 6-month internship beginning in February, March, "
     "April, May, or June 2027", []),
    ("Ability to commit to a full-time (40 hours/week Monday - Friday) for a "
     "minimum 12 week internship", []),
    # Spring is not noise: it is a framework too.
    ("A graduation date in Fall 2027 or Spring 2028 with a Bachelor's degree",
     ["Spring", "Bachelor"]),
    # Words joined by a slash are judged apart, so a Software Engineering
    # degree can back this line.
    ("Previous Computer Science/Software Engineering internship experience",
     ["Computer", "Science", "Software", "Engineering"]),
    ("Experience with C/C++ or Rust", ["C++", "Rust"]),
])
def test_calendar_words_and_joined_words_are_not_names(line, expected):
    assert jobhunt.salient_terms(line) == expected


def test_the_postings_own_company_and_location_are_not_requirements(profile):
    """"In office in Austin, TX" says where the job is; nothing in a profile
    backs a city, and the report called it a gap."""
    job = Job(title="Software Engineer Intern", company="Cloudflare",
              location="Austin, US",
              requirements=["In office 3-5 days a week in Austin, TX.",
                            "Experience with Cloudflare Workers."])
    found = jobhunt.score(job, profile)
    assert "Austin" not in found.gaps
    assert "Cloudflare" not in found.gaps
    assert "Workers" in found.gaps          # the product is still asked for


def test_a_skill_the_candidate_lists_outranks_noise_and_the_company(profile):
    """Spring is a season and a framework; MongoDB is the company hiring and
    the database it asks for. Someone who lists them is asked about them."""
    listed = jobhunt.clone(profile, skills=["Spring", "MongoDB"])
    job = Job(title="Engineer", company="MongoDB",
              requirements=["Experience with Spring", "Experience with MongoDB"])
    found = jobhunt.score(job, listed)
    assert [r.status for r in found.required] == [EVIDENCED, EVIDENCED]


def test_a_calendar_word_in_the_summary_is_not_parroting(profile):
    """Writing "Summer 2027" in a CV summary tripped the parroting wire,
    because the posting asked for a Summer internship and no profile
    contains the word."""
    job = Job(title="Intern", company="Scale AI",
              requirements=["Available for a Summer 2027 internship"])
    document = jobhunt.tailor(profile, job, {"summary": "Applying for Summer 2027.",
                                             "roles": [{"index": 0}], "projects": [],
                                             "skills": []})
    found = jobhunt.score(job, profile, document, when="after")
    assert not found.parroting


def test_sentence_initial_words_are_not_gaps(profile):
    job = Job(title="Engineer", requirements=["Build data pipelines in Python",
                                              "Own the on-call rota"])
    found = jobhunt.score(job, profile)
    assert not {"Build", "Own"} & set(found.gaps)
    assert found.required[0].status == EVIDENCED       # Python, and backed
    assert found.required[1].status == NOT_CHECKABLE   # nothing named at all


def test_tools_that_open_a_line_are_found_in_the_bullets(profile):
    """The tools are only in bullets, so nothing but the line says they are
    names - and the posting's own prose uses go, react and swift as the
    ordinary words they also are."""
    doer = jobhunt.clone(profile, skills=[], projects=[], experience=[Role(
        position="Engineer", company="Acme", start="2020", end="2024",
        bullets=["Ran Linux hosts and Go services on Kubernetes, built with Terraform.",
                 "Shipped React and Vue front ends, designed in Figma.",
                 "Wrote a Swift app for iOS."])])
    job = Job(title="Engineer",
              description="We move fast and go deep. When incidents happen we react "
                          "quickly. Spark curiosity, swift decisions.",
              requirements=["Linux administration", "Go services at scale",
                            "Figma for design", "Terraform to manage infrastructure",
                            "React for building UIs",
                            "Kubernetes for container orchestration",
                            "Swift for iOS apps", "Go or Rust experience",
                            "Experience with React or Vue",
                            "Own the ingestion pipelines", "Mentor junior engineers",
                            "Excellent Problem Solving Skills"])
    found = jobhunt.score(job, doer)
    assert [r.status for r in found.required] == [EVIDENCED] * 9 + [NOT_CHECKABLE] * 3
    assert not found.gaps


def test_a_title_case_line_names_nothing(profile):
    """Title-cased requirement lines used to report Problem and Solving as gaps."""
    job = Job(title="Engineer", requirements=["Excellent Problem Solving Skills"])
    found = jobhunt.score(job, profile)
    assert found.required[0].status == NOT_CHECKABLE
    assert not found.gaps


def test_a_tool_the_candidate_lists_is_a_name_wherever_it_sits(profile):
    """Airflow is only on one role's skills list, and it opens the line."""
    job = Job(title="Engineer", requirements=["Airflow experience in production"])
    found = jobhunt.score(job, profile)
    assert found.required[0].status == EVIDENCED


def test_a_quantity_adjective_is_not_a_requirement(profile):
    """"Significant experience..." asks for experience, not for Significant."""
    wordy = jobhunt.clone(JOB, **{"requirements": [
        "Significant experience delivering large-scale infrastructure, HPC included"]})
    found = jobhunt.score(wordy, profile)
    assert "Significant" not in found.gaps
    assert "HPC" in found.gaps


def test_evidence_is_quoted_as_the_person_wrote_it(profile, job):
    """It is their own sentence, printed beside a claim so they can judge it
    rather than trust a number. It spent a while URL-encoded, because a helper
    in the outreach section was also called `_quote` and won.
    """
    found = jobhunt.score(job, profile)
    quotes = [e.quote for r in found.requirements for e in r.evidence]
    assert quotes, "nothing was evidenced, so nothing was quoted"
    for quote in quotes:
        assert "+" not in quote or " " in quote, f"URL-encoded: {quote!r}"
        assert "%2" not in quote and "%3" not in quote, f"URL-encoded: {quote!r}"
        # and it really is a line from the profile
        assert any(quote.rstrip("…") in " ".join(b.split())
                   for role in profile.experience for b in role.bullets) \
            or any(quote.rstrip("…") in " ".join(s.split())
                   for s in profile.skills + [profile.summary]) \
            or quote, quote


def test_a_long_bullet_is_cut_with_an_ellipsis(profile, job):
    long = "Rewrote the dbt models " * 20
    profile.experience[0].bullets.append(long)
    found = jobhunt.score(job, profile)
    for r in found.requirements:
        for e in r.evidence:
            assert len(e.quote) <= 160, len(e.quote)
