# Archive gems (machine list)

**Date**: 2026-09-20  
**Method**: extractive only (no live LLM endpoint this run)  
**Candidates**: 89 · **Rows**: 60  
**Curated reading**: `ARCHIVE_GEMS.md` (human pass over this pack)

These rows are cited excerpts the frames pointed at. Bots and `utACK`-only lines are dropped. Read the curated file first.

| Era | Frame | PR | Quote |
|-----|-------|---:|-------|
| 2022+ | funnel | 34329 | I went over the change, my biggest concern is the race in remove and the verbose tests and some minor commit churn - left examples for each suggestion to speed up the process. Concept ACK |
| 2022+ | funnel | 33843 | Concept NACK to deferring adding tests until after adding a new feature. |
| 2022+ | funnel | 33682 | Concept NACK Adding a new startup option (`-datacarriercount`) increases policy heterogeneity across the network. As discussed in the [motivation](https://github.com/bitcoin/bitcoin/issues/33595), more heterogeneity → le… |
| 2022+ | funnel | 31012 | Ok, then I am nack-ish on this. Generally, test code should follow real code, not the other way round, unless there is a reason. Saving 15 lines of test-only code seems a weak reason to me, but I don't mind if others lik… |
| 2022+ | funnel | 30928 | Will not nack this pr since I don't think consequences are great, but I would prefer not to see this PR merged. I don't think putting "error while formatting log message" in a std::string and then returning that std::str… |
| 2022+ | funnel | 29520 | NACK This option is useless and adding more "filters" to maintain this will be a waste of time for everyone. There are lot of important and useful things which do not get added in bitcoin core because it will be a mainte… |
| 2022+ | funnel | 27742 | Offline feedback suggested I clarify what I mean by "approach feedback welcome" before "I open separate PRs." This is a large project, and the first few p2p commits essentially define the interface. I'd like to get rough… |
| 2022+ | funnel | 27086 | > I agree with @sipa, with a stronger emphasis that I would probably NACK this change because the cost of this fix is too high, and the privacy gain is too low. Yeah, Approach NACK. I may be convinced that doing *somethi… |
| 2022+ | funnel | 26469 | > Concept NACK. See also more reasonable (yet still rejected) proposals #8457, #16439, #14858, #16345, #16317 These are my thoughts about those particular listed PRs. I would disagree that they are all 'more reasonable' … |
| taproot | funnel | 23896 | Concept NACK. The documentation should be enough to run the tests, I think if a website has useful tips about it, then, it would be better to include the tips in the docs, instead of a reference to an external website. |
| taproot | funnel | 23443 | Did you think about a `-disablerecon` command or something similar, to not activate Erlay until all the parts have been merged? Providing the opportunity to opt in/out would probably make sense anyway, but it would also … |
| taproot | funnel | 23114 | Concept NACK to using a subtree for non-concensus-critical libraries. At the very least, there should be a way to use a system install. |
| taproot | funnel | 21859 | (don't merge this yet, as it includes the as-of-yet unmerged sipa/minisketch#44) |
| taproot | funnel | 21702 | At this point I've went through all code in this PR pretty thoroughly (I was really hoping to find something wrong to snatch that bounty 😔). The only thing (implementation wise) I have a problem w/ at this point is the c… |
| taproot | funnel | 21515 | rebroad: > How can I help test this? I've been running it for a few hours so far on mainnet, but haven't noticed much difference compared to the master branch. > I've been testing this, and so far I've found that the eff… |
| taproot | funnel | 19168 | I think this renaming is unwise and am NACK on it. Why: - Semi-subjective: The new name is more confusing. "Set to true to not do something" is not an improvement in clarity. - Objective: The change has consequences that… |
| taproot | funnel | 16653 | Concept NACK until it is being used actively. I don't think unused code is good, it just makes the binary bigger |
| taproot | funnel | 16487 | > For a wallet dealing correctly with its transactions for one chainstate is hard enough, now if it has to filter them, that's need more thought... I think for now assumeutxo is just supposed to be useful for new wallets… |
| taproot | funnel | 16440 | Abstract, tentative concept NACK: I'm not convinced BIP322 is itself a good idea as-is. Its multiple-proofs concept seems ripe to encourage misuse of signatures as a false "proof" of spend-ability rather than simply prov… |
| taproot | funnel | 16355 | utACK. Could you fix up Rus's nit and this should be mergeable. |
| taproot | funnel | 15976 | Thanks for the good feedback @Sjors @MarcoFalke @ryanofsky. I agree with the comments so far and have incorporated all of them aside from those noted above. Initially I hadn't touched the global `Flush` functions because… |
| taproot | funnel | 15606 | @Sjors thanks very much for testing. > it crashed when I stopped the node and started it again You found a bug in how the init process interacts with an assumed-valid chainstate. I needed to add `nChainTx` reconstruction… |
| taproot | funnel | 12407 | Slight utACK 6af17e40890651e5e5f5968a1a131c6a48ce998c. Slight because I don't know all the implications of adding the new InvalidBlockFound calls. New test code looks great. I'd find the main commit ("Do the proper Inval… |
| segwit | funnel | 10102 | > Using the console I'm getting the following error: > ![](https://user-images.githubusercontent.com/10217/44627206-060c7380-a92a-11e8-9cfe-84842cff0f66.png) Rpc help error is fixed now. It was caused by `signrawtransact… |


**Generated by**: `scripts/reporting/generate_from_templates.py`
