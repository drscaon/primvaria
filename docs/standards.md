# How Primvaria uses standards

Many of the parts the generators make follow a published standard: a screw
is an ISO 4762 cap screw, a connector an IEC 60807-3 D-sub, a ballast an
EN 13450 grading. Standards are copyrighted documents, sold by the bodies
that write them (ISO, IEC, CEN, DIN, JIS and others). Primvaria uses what a
standard describes, never the document itself.

## What the repositories hold

- **Numbers only.** Dimensions, tolerances, limits and the coefficients of
  formulas, and only those a generator uses: the sizes and the columns it
  builds parts from, not a standard's tables.
- **A public source for every number.** A manufacturer's datasheet or
  catalogue, a public table, an engineering handbook. Each generator's
  `docs/sources.md` names it next to the value, and a test fails on a value
  without one. The standards themselves are not consulted.
- **A standard's number as a name.** "ISO 4762" says which kind of part a
  file is; it is not a source.

## What they never hold

- Text from a standard: its clauses, notes, definitions or scope, quoted or
  closely paraphrased.
- A table as a standard prints it: its layout, its notes, its full set of
  rows and columns.
- Figures or drawings from a standard.
- A copy of a standard, a link to a copy, or a link to a sample or preview of
  one.

## How the text is written

Every page, comment, docstring and field description is written in our own
words, and says what the generator does with a value, not what a standard
requires. Where no public source gives a value, it is an estimate, marked as
such with what it rests on, or the part waits.

## How it is checked

The pull request checklist of the five repositories has a line for it, and
each change that adds a part is reviewed against this page before it is
merged.
