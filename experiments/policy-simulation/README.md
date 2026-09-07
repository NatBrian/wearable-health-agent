# Policy simulation: our code, scored against labels we planted

**This is the weakest evidence in the repository, and it was until 7 September 2026 the
most prominently quoted.**

Forty synthetic cases. The ground truth is a label this project injected. A simulated person
answers every question truthfully, immediately, and with perfect recall.

## What it measures

Whether a question-asking policy recovers a cause that the simulation itself put there.

## What it does not measure

Anything about a person. It cannot tell you that asking a real human a question improves
anything, because no human was involved at any point. Real people misremember, answer late,
answer vaguely, decline, or are not sure. None of that is modelled.

The headline it used to be quoted for, that deciding from sensor data alone scores at
chance, is a property of a simulation whose difficulty we chose when we built it. The even
split between infections and mimics is ours too: with infections only, a policy that always
answered "illness" would score one hundred percent.

The design reason that survives without any of these numbers is plain enough to state in
words. A wrist sensor sees one number. Infection, alcohol, a hard evening session, a bad
night's sleep and a vaccination all move that number in the same direction. Asking is the
only way this system can tell them apart, so it asks.
