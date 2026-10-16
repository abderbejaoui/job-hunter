"""Tailoring: the boundary CONTRIBUTING asks to be pinned by a test.

A generator may select, reorder and reword facts from the profile. It may not add
an employer, a date, a course, a tool or a metric. Most of that is structural
here - the model answers with indices - so these tests pin the structure as much
as the prompt.
"""



import jobhunt
import pytest

REPLY = {
    "summary": "Data engineer with production pipeline experience.",
    "roles": [{"index": 0, "bullets": ["Cut ETL runtime by 35% by rewriting the dbt models."]},
              {"index": 1, "bullets": ["Built the finance dashboards used by 40 people."]}],
    "projects": [0],
    "skills": ["Python", "dbt", "SQL"],
}


# --- assembly ------------------------------------------------------------

def test_roles_keep_the_profile_order_not_the_model_s(profile, job):
    """Ranked by relevance, a past role lands above the current one."""
    document = jobhunt.tailor(profile, job, {**REPLY, "roles": [{"index": 1}, {"index": 0}]})
    assert [r.company for r in document.experience] == ["Acme", "Beta"]


def test_the_model_still_chooses_which_roles_appear(profile, job):
    document = jobhunt.tailor(profile, job, {**REPLY, "roles": [{"index": 1}]})
    assert [r.company for r in document.experience] == ["Beta"]


def test_a_dropped_role_is_reported(profile, job):
    document = jobhunt.tailor(profile, job, {**REPLY, "roles": [{"index": 0}]})
    left_out = [i for i in document.all_issues if "Left off" in i.message]
    assert left_out and "Beta" in left_out[0].message


def test_nothing_is_reported_when_every_role_is_kept(profile, job):
    document = jobhunt.tailor(profile, job, {**REPLY, "roles": [{"index": 0}, {"index": 1}]})
    assert not any("Left off" in i.message for i in document.all_issues)


def test_a_role_with_no_bullets_falls_back_to_the_profile(profile, job):
    document = jobhunt.tailor(profile, job, {**REPLY, "roles": [{"index": 0, "bullets": []}]})
    assert document.experience[0].bullets == profile.experience[0].bullets


def test_out_of_range_and_duplicate_indices_are_dropped(profile, job):
    document = jobhunt.tailor(profile, job, {**REPLY, "roles": [
        {"index": 0}, {"index": 0}, {"index": 99}, {"index": -1}, {"index": "x"}]})
    assert [r.company for r in document.experience] == ["Acme"]


def test_index_accepted_in_the_shapes_models_use(profile, job):
    for entry in (1, "1", {"index": 1}, {"i": 1}, {"index": "1"}):
        document = jobhunt.tailor(profile, job, {**REPLY, "roles": [entry]})
        assert [r.company for r in document.experience] == ["Beta"], entry


def test_no_roles_selected_keeps_them_all_and_says_so(profile, job):
    document = jobhunt.tailor(profile, job, {**REPLY, "roles": []})
    assert len(document.experience) == len(profile.experience)
    assert any("did not select" in i.message for i in document.issues)


def test_bullets_are_capped(profile, job):
    many = [f"Did thing number {i} at work." for i in range(20)]
    document = jobhunt.tailor(profile, job, {**REPLY, "roles": [{"index": 0, "bullets": many}]})
    assert len(document.experience[0].bullets) == jobhunt.MAX_BULLETS


def test_bullet_characters_are_stripped(profile, job):
    document = jobhunt.tailor(profile, job, {**REPLY, "roles": [
        {"index": 0, "bullets": ["- Mentored two junior analysts.", "  ", "• Cut runtime."]}]})
    assert document.experience[0].bullets == ["Mentored two junior analysts.", "Cut runtime."]


def test_skills_fall_back_to_the_profile_when_none_survive(profile, job):
    document = jobhunt.tailor(profile, job, {**REPLY, "skills": ["Kafka"]})
    assert document.skills == profile.skills


def test_skills_may_come_from_a_role_or_a_project(profile, job):
    """Airflow is only listed on a role; Python only on a project. Both are real."""
    document = jobhunt.tailor(profile, job, {**REPLY, "skills": ["Airflow", "Python"]})
    assert document.skills == ["Airflow", "Python"]


def test_summary_falls_back_to_the_profile(profile, job):
    document = jobhunt.tailor(profile, job, {**REPLY, "summary": ""})
    assert document.summary == profile.summary


def test_projects_are_selected_not_reworded(profile, job):
    document = jobhunt.tailor(profile, job, {**REPLY, "projects": [{"index": 0,
                                                                 "description": "Rewritten!"}]})
    assert document.projects == [profile.projects[0]]


# --- placeholders: template text left in, reported and never blocked -------

@pytest.mark.parametrize("line", [
    "Grew revenue at [Company] by 20%.",
    "Joined [MONTH] 2027.",
    "Cut costs by XX%.",
    "Saved $XXk a year.",
    "Led the move to <Company>'s new platform.",
    "Hello {{company}} team.",
    "Your Name",
    "Lorem ipsum dolor sit amet.",
    "TODO: add the figure.",
    "Start date TBD.",
    "FIXME",
])
def test_a_placeholder_in_the_profile_is_a_warning(profile, line):
    profile.experience[0].bullets[0] = line
    said = [i for i in profile.report() if "placeholder" in i.message]
    assert [i.path for i in said] == ["experience[0].bullets[0]"], line
    assert said[0].severity == jobhunt.WARNING
    assert not profile.blocking_issues(), "a warning, never a block"


@pytest.mark.parametrize("line", [
    "Built a TODO app in React with 300 users.",   # names a thing
    "Ein TODO-Listen-Tool für das Team gebaut.",
    "Lideré todo el equipo de datos.",              # Spanish "all"
    "Werkstudent Data Engineering [m/w/d]",
    "Wrote up the design in [the RFC](https://example.com/rfc).",
    "Moved the service to List<String> generics.",
    "Shipped the XXL size range.",
    "Answered to the CTO; your name goes on the release notes.",
])
def test_honest_prose_is_not_a_placeholder(profile, line):
    profile.experience[0].bullets[0] = line
    assert not [i for i in profile.report() if "placeholder" in i.message], line


def test_the_posting_s_title_is_not_read_as_a_placeholder(profile, job):
    """"Data Engineer [Remote]" is the employer's text, carried on the tailored
    CV as its label, and not something the candidate left unfilled."""
    job.title = "Data Engineer [Remote]"
    document = jobhunt.tailor(profile, job, REPLY)
    assert "[Remote]" in document.job_label
    assert not [i for i in document.all_issues if "placeholder" in i.message]


def test_a_placeholder_in_a_letter_is_a_warning(profile, job):
    letter = jobhunt.write_letter(profile, job, {
        "greeting": "Dear [Hiring Manager],", "closing": "Kind regards,",
        "paragraphs": ["I cut ETL runtime by 35%."]})
    said = [i for i in letter.all_issues if "placeholder" in i.message]
    assert [i.path for i in said] == ["greeting"] and "[Hiring Manager]" in said[0].message
    assert not letter.blocking


# --- the shape of the page ------------------------------------------------

def test_the_shape_of_the_page_is_reported_but_never_blocks(profile, job):
    """What the model picks is cut to eight bullets a role, so only a role the
    model left unselected - shown as written - can pass the review's line."""
    long = "word " * 40
    profile.experience[0].bullets = ["Responsible for the pipelines.", long.strip(),
                                     *[f"Did thing {i}." for i in range(7)]]
    document = jobhunt.tailor(profile, job, {
        "summary": "long " * 70, "roles": [], "projects": [], "skills": []})
    said = {(i.path, i.severity) for i in document.issues}
    assert ("summary", jobhunt.WARNING) in said
    assert ("experience[0]", jobhunt.WARNING) in said                 # 9 bullets
    assert ("experience[0].bullets[0]", jobhunt.INFO) in said         # the opener
    assert ("experience[0].bullets[1]", jobhunt.INFO) in said         # the length
    assert not document.blocking


def test_a_tidy_document_gets_no_layout_notes(profile, job):
    document = jobhunt.tailor(profile, job, REPLY)
    assert not [i for i in document.issues
                if i.path in ("summary", "skills") or "words" in i.message]


def test_coaching_asks_the_review_s_question_for_each_bullet_without_a_figure():
    profile = jobhunt.Profile(experience=[jobhunt.Role(
        position="Engineer", company="Acme",
        bullets=["Responsible for the CI/CD pipelines.", "Cut ETL runtime by 35%."])])
    page = jobhunt.coaching(profile)
    assert "How long did a release take before this, and after?" in page
    assert "Starts with 'responsible for'" in page
    assert "ok  Cut ETL runtime by 35%." in page
    assert "1 bullet(s) carry no figure" in page
    assert "Never fill a number in yourself" in page


def test_coaching_speaks_to_every_bullet_not_the_review_s_first_six():
    """The review page names six lines per dimension; coaching asks about all."""
    profile = jobhunt.Profile(experience=[jobhunt.Role(
        company="Acme", bullets=[f"Wrote the runbook for service {c}." for c in "ABCDEFGH"])])
    page = jobhunt.coaching(profile)
    assert "8 bullet(s) carry no figure" in page
    assert page.count("no figure -> ask:") == 8


def test_the_document_carries_the_job_it_was_made_for(profile, job):
    document = jobhunt.tailor(profile, job, REPLY)
    assert document.job_label == "Senior Data Engineer at Zeta"
    assert document.job_slug == "zeta-senior-data-engineer"




def test_a_dropped_role_is_a_warning_not_a_blocker(profile, job):
    """Leaving Beta off is reported so the candidate can disagree, and it
    must not stop the document being exported."""
    document = jobhunt.tailor(profile, job, {**REPLY, "roles": [
        {"index": 0, "bullets": ["Ran Kubernetes."]}]})
    assert any("Left off" in i.message for i in document.issues)
    assert not document.blocking