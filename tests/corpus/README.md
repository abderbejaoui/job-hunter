# The corpus

Five profiles that stand for five kinds of person this tool is used by. None
is anyone real. `tests/test_corpus.py` renders each one every way and asks the
questions a recruiter would; `tools/gallery.py` renders them for eyes.

Links are on `example.com`, `example.org` and `example.net`, emails on
`example.com`, and a phone number is in Ofcom's range for drama or left
blank: an invented career must not point at a real person's account.

| file | who | what it exercises |
|---|---|---|
| `student.yaml` | a final-year student, two internships, four projects | Education first, one page, the project figures |
| `career-changer.yaml` | a teacher moving into data | mixed history, transferable bullets; every role ends on a date, because nine years and some months of "Present" turned into a two-page budget a month later |
| `senior.yaml` | fourteen years, five roles | the two-page budget, long roles trimmed |
| `non-tech.yaml` | a nurse and ward manager | no projects, many certifications, a non-software vocabulary |
| `french.yaml` | a French profile in French, `language: fr` | accents and French months through every renderer, including TeX |

Add one when a kind of CV goes wrong that these do not cover, and say in the
table what it is there to catch.
