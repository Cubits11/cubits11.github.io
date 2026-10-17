# Five unfamiliar readers — owner-run test

Status: NOT RUN. Publication remains blocked. No participant results have been supplied.

The owner will recruit and run this test. Use five distinct people who have not seen this site, its films, this repair discussion, or the answer criteria. They must be humans; assistants and agents do not count. Keep all five results, including failures. Do not replace a failed reader after seeing an answer.

## Candidate to show

Use the repaired local candidate, not the older public website. The current preview is http://127.0.0.1:8768/. It works on the owner's computer while its preview server is running. For a remote reader, use a session that lets the reader operate that candidate; a facilitator clicking on the reader's behalf does not demonstrate a one-click task.

The film is **The Missing Column, Counted**, `/films/the-missing-column-census/` (40 seconds). It counts which public evaluations keep the joint record, meaning what happened to both guards on the same item. The film task tests exactly that. It does not test the shared-misses construction, which this film does not show. Use the watch page, rather than the source animation page, so its real proof link is available.

The final packaged candidate is already bound before collection. If you intentionally prepare a new candidate before the first reader, bind it with `python scripts/publication_gate.py --bind`. This records the tested page, style, script and media hashes. Then make the blank worksheet with `python scripts/publication_gate.py --template`. A changed tested artifact requires a fresh test of the changed candidate. Do not rebind old observations to new pages.

## Read this to each reader

Do not show the answer criteria below to participants. Use P01 through P05 as anonymous IDs. Record date, device, browser, viewport and exact answers. Record what happened, including uncertainty and assistance. Do not explain the site's purpose or what the film counts first.

1. Open the homepage at its top. Once it is loaded, say: **“You have 20 seconds. Tell me what this site is about and show me how you would contact its owner.”** Start the timer on that prompt. Allow normal scrolling. Stop at 20 seconds. Record the reader's words, the contact destination they identify, and the time at which both tasks were completed. They need not send a message. Give no hints or correction.
2. Open the film watch page and let them watch the entire film once, at normal speed, with normal controls. Then say: **“In one sentence, what does the film say is missing in most evaluations?”** Record the answer verbatim before discussing it. There is no time cutoff for this task. Record whether they watched the whole film and used any replay or help.
3. With the real links below that player visible, say: **“Open the 60-second proof.”** Let the reader operate the page. Record activations and the destination. Normal pointer movement or keyboard focus movement is allowed. One click or one Enter/Space activation of the link must land on `/try/`. Do not activate it for them. There is no time cutoff for this task.

Complete and record all three tasks for each of the five readers. Do not teach between tasks. Debrief after their observations have been recorded. If any step cannot be observed reliably, mark it incomplete; do not infer success. An observed failure is still a result: write “No response” or “Not reached” when that is what happened, rather than leaving a field blank. Record an incomplete film viewing or zero proof activations as failures.

## Score before looking at totals

Use these criteria, fixed before the first session:

- **Homepage subject:** the answer identifies AI guardrails and the question of their shared failures, combined misses, or what separate scores leave unknown. Equivalent plain language counts. A generic answer such as “an AI website” is insufficient.
- **Homepage contact:** the reader identifies the owner's working email link/address on the homepage. They need not send email. The homepage task passes only if both subject and contact succeed within the same 20-second window.
- **Missing column:** the sentence states both parts. (1) What is missing: the joint record, meaning what happened to both guards on the same item (equivalently, the joint column or joint evidence). (2) The scale: most evaluations lack it, or 14 of 20 lack it, or only 5 of 20 keep any. Exact numbers and specialist terms are unnecessary. Passing examples: “Most evaluations don't record what happened to both guards on the same item.” “14 out of 20 evaluations don't have the joint column.” “Only 5 of 20 keep any joint evidence, none at matched thresholds.” Failing examples: “Guards fail together sometimes.” (no joint record, no scale; could be said without watching). “Individual scores don't tell you how often guards fail together.” (true, but it is the shared-misses answer, not what this film counts). “The film was about AI safety.” (no content). An answer missing either part fails.
- **Proof:** one actual activation of the real post-player proof link reaches `/try/`. An instruction, a visible URL, or a facilitator's click is not a completed task.

The gate passes only when **at least four of the same five readers pass the homepage task, at least four pass the missing-column task, and at least four pass the proof task**. The four need not be the same people across tasks. Do not average scores across tasks.

If any threshold is missed, preserve all answers and failed counts, change the relevant page/film, bind a new candidate, and run the full test with five new unfamiliar readers. Do not combine pre-change and post-change participants into one passing group.

## Record and return

Use the blank five-reader worksheet produced by the template command. Fill it only from observed sessions, then transfer the completed real records into `publication/readers.json`. Its facilitator attestation records that the participants were distinct, unfamiliar humans; software cannot independently establish that fact. Keep names and contact details out of the public record. Store any private recordings separately with consent; anonymous verbatim answers and observations are sufficient for the worksheet.

Run `python scripts/publication_gate.py` after recording the results. A passing result checks the supplied evidence and current artifact bindings. It does not establish scientific validity, population-level comprehension, accessibility, or the authenticity of an unverified attestation. Five readers are a bounded usability gate.

Publication is still held until the title change has also been applied and verified, all 12 phone cuts have current audited renders, and this real reader test meets all three thresholds. The separate Ghost Visualizer title patch is prepared locally; the current public title has not been changed during this work.
