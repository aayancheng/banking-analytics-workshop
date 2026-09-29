// Layout fixes for the validation PDF, loaded by _quarto-validation.yml.

// Quarto's glossary rule pulls a definition up under its term (top: -0.4em) and the two
// overlap; keep the same look with a small positive gap.
#show terms.item: it => block(breakable: false, below: 0.9em)[
  #text(weight: "bold")[#it.term]
  #block(inset: (left: 1.5em, top: 0.2em))[#it.description]
]

// A code identifier such as score.band_booked.A.defaults cannot wrap, so in a narrow
// table cell it runs over the next column. Offer a line-break point (a zero-width
// space) after each underscore, slash and letter-dot (never inside a number), inside table cells only.
#show table.cell: it => {
  show raw.where(block: false): r => {
    if r.text.contains("\u{200B}") or not r.text.contains(regex("[_/]|[A-Za-z]\\.")) { r } else {
      raw(r.text.replace(regex("[_/]|[A-Za-z]\\."), m => m.text + "\u{200B}"))
    }
  }
  show regex("[_/]|[A-Za-z]\\."): t => t + "\u{200B}"
  it
}
