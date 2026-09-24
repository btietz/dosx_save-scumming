Divinity: Original sin has anti-save scumming measures built in, using a
persistent PRNG (pseudo-random number generator).  But did you know?  You can
abuse this system!  By leaving junk containers (barrels, etc) unopened, when
you find a high value container (chest, ornate chest) you can save and
backtrack to open those junk containers, which manipulates the PRNG seed.  Then
when you open the high value container, the loot will differ!  It may be better,
it may be worse, but if you open junk containers that you've left behind and
unopened in various orders, you can manipulate the PRNG seed in such a way that
you might stumble onto a high value loot drop from the high value container.

Problem: doing that by hand, what we think are random actions actually aren't.
This script suggests totally randomized open sequences to try while save
scumming.  Load last save, open junk containers in the first sequence, then
finish off with the high value target container.  If you get junk, load that
last save, open junk containers in the second sequence, and try again.

To use it, just populate the areas array, and run it!

There are a lot of options to expedite the run time:

--sequential / -s: areas are forced to be sequential.  Useful if containers are
widely separated, to minimize travel time.  This is mostly mitigated by
splitting your party, sending different characters to different areas, but the
feature remains.  It's basically an artifact from before I figured out that
trick.

--randomly-terminate-exploration X: if the number of junk containers available
is massive so the run time explodes, but you want to make best use of them, this
option will randomly terminate the paths it is considering.  A higher value of X
(an integer) means more aggressive termination.  If the script is taking way too
long, dial this up.

--longer X / -l X: favor longer solutions.  X is an integer, the higher the
value of X, the longer the solutions.

--num-solutions X / -n X: how many solutions to randomly select and output at
the end.

--preserve-rares / -p / -p2: if you have several high value loot containers,
and a few rare junk containers of differing types, so you want to save them for
later save scumming to better manipulate the PRNG seed, this option makes sure
that a suggested opening order only ever includes 1 or 2 rare ones.  "Rare" is
based on container count in the input array.  Use -p2 to allow two in a given
suggested sequence.

Using this script means manipulating the areas array and nested dicts in python.
If you're here, you know what that means, and you'll figure it out.  :-D
