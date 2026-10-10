# Blinded patch rubric

Coders see the pull request description and the patch. Author, reviewer names, and outcome are not in the bundle. Score the patch that is in front of you. Do not look up the pull request.

Each item is an integer from 1 to 5.

## Correctness

Does the change do what it says, without an obvious logic error in the lines shown?

1. The change contradicts its own description, or a logic error is visible in the patch (a condition inverted, a resource freed twice, a check that can never pass).
3. The change matches the description on the main path. An edge path is unhandled and the patch does not say so.
5. The change matches the description, and the edge paths the description names are handled in the lines shown.

## Scope discipline

Does the patch stay inside the job it describes?

1. The patch edits unrelated subsystems, reformats untouched code, or renames symbols the description does not mention.
3. The patch does the job and also includes one drive-by edit that is not required for it.
5. Every hunk is required for the job the description names.

## Test coverage

Do the tests in the patch exercise the behavior the description claims?

1. The description claims a behavior change and the patch contains no test.
3. A test covers the main path and not the failure path the description mentions.
5. Tests cover the main path and the failure path the description mentions. A documentation or comment-only change scores 5 when there is no behavior to test.

## Clarity of description

Can a reader tell what changed, and why, from the description alone?

1. The description is empty, or it names a subsystem without saying what changed.
3. The description says what changed and not why, or the why is a single vague clause.
5. The description says what changed, why, and what the reader should look at in the patch.

## What the scores are not

A high score is not a merge decision. A low score is not a verdict on the author. The scorer does not record whether the pull request merged.
