---
name: jobhunt-posting
description: >
  Read a job posting from a URL (or pasted text) into job.yaml - title,
  company, requirements, and the page text it came from. Use when someone gives
  a job link and you need the posting as structured data.
argument-hint: <job-url>
allowed-tools: Bash, Read, Write
---

# Read the posting

Two steps, because only one needs judgement.

The script is next to this file -
`${CLAUDE_PLUGIN_ROOT}/skills/jobhunt-posting/posting.py` under a plugin install.

**Do not use `WebFetch`.** Greenhouse, Lever and Workday render descriptions
client-side; `WebFetch` gets a loading spinner. This loads the page in the
browser already on the machine.

## 1. Load the page

```bash
python3 posting.py "https://boards.greenhouse.io/acme/jobs/42"
```

It prints the run directory. Read `page.txt` from it.

**Exit 1?** The posting is behind a login wall, or the page gave back almost
nothing. Ask for the description as text and use it:

```bash
python3 posting.py --text pasted.txt "https://the-original-url"
```

Never work around a wall. Working around it means inventing a job description,
and everything downstream is then tailored to something imaginary.

## 2. Write what you read

Write JSON to a file, then parse it. Every field is optional; leave out what
the posting does not say rather than inferring it.

```json
{
  "title": "Senior Data Engineer",
  "company": "Acme",
  "location": "Munich, Germany",
  "workplace": "hybrid",
  "employment_type": "Full-time",
  "salary": "70-85k EUR",
  "language": "en",
  "description": "What the role is, in a paragraph or two.",
  "responsibilities": ["Own the ingestion pipelines"],
  "requirements": ["3+ years with Python", "Strong SQL"],
  "nice_to_have": ["Kafka"],
  "keywords": ["Python", "SQL", "dbt"]
}
```

```bash
python3 posting.py --parse job.json --run <run>
```

The run is renamed to `<date>-<company>-<role>` once the job has a name, and
the new path is printed. Use that path from then on. A different posting that
names the same way on the same day - the same title at the same company in
another city - gets `-2`, `-3` on the end, so it starts clean.

**`kept` not empty?** This posting was already read today, from the same URL
(or the same pasted text), and `kept` lists what the run holds from that
earlier read - `cv.yaml`, `letter.yaml`, `fit-before.md` and so on. `page.txt`
and `job.yaml` are now the new read. If the requirements, title or location
changed since, everything in `kept` is aimed at a posting that no longer
exists: score fit `--when before` again, re-tailor, and redo whatever else is
listed. If you cannot tell whether it changed, redo them. Only when you know
nothing material changed, keep them, and tell the person you did.

## Getting it right

- **`requirements` is the field that matters.** It is what fit is scored
  against. One requirement per entry, in the posting's own words - do not merge
  two into one or split one into two.
- **Keep `required` and `nice_to_have` apart** as the posting divides them.
- **`language`** is the language the posting is written in, as a two-letter
  code. The letter is written in it.
- **Do not paraphrase a requirement into something the candidate has.** That is
  the failure this whole tool exists to prevent, and it starts here.
- `url`, `brand_color` and `fetched_at` are filled in from what was observed.
  Anything you write for them is ignored.
