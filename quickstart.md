# A Quick Start Guide For The AR (Auto-Rebalancer)

## Here is a quick thread to get you started with the AR in LNDg. It can take a bit to get the hang of it but once you do, it's very powerful. 💪 
1. In the channels table, identify a good paying and high outflow channel. This is a great channel to start learning with as attempts are based on the enabled or targeted channel. Also check that the peer's fees on the other side is less than yours else it could never rebalance. 

2. Once you have identified a well earning outflow channel, use the enable button on the right side to start targeting this channel to be refilled with outbound liquidity. We know this channel flows out well and earns sats, lets keep it filled and busy routing! 😎 

3. Repeat this process for all channels that earn well and you do not want to lose outbound liquidity on (a good example would be LOOP). Don't worry too much about keeping each channel at 50/50 balance but instead keep your focus on putting liquidity back where it earns you sats. 

4. Now that you have a few channels enabled and targeted, you can drop the iTarget% for each enabled channel down to your desired preference. If you keep the iTarget% at 100 then nothing will ever happen because the inbound liquidity can never go above 100. 

5. To get the AR working on this channel, the inbound liquidity on the channel must be above the iTarget% and thus the 100 would never do anything. Setting an iTarget% of 60 however would refill this channel with outbound liquidity until the inbound liquidity fell below 60%. 

6. A tip when entering a new value into the iTarget% bow, you must hit enter afterwards for the value to be saved! Now that we understand how to refill channels, lets talk about where we have to pull the liquidity from in order to refill these channels. 

7. One setting that will affect which channels can feed others during refilling is AR-Outbound%. This can be found in the AR settings table. If you don't see a particular setting in the table yet, try to set it using the form just below the table.  When targeting a channel to be refilled, LNDg will use any channel that is not already enabled AND the outbound liquidity of the channel is greater than the AR-Outbound%. Advanced users may prefer to update the oTarget% for each channel, which overrides this global setting. 

8. Just to recap, we are enabling channels we want to refill with outbound and those channels will be fed liquidity by channels that are not enabled. We can control how far to push the inbound liquidity down during refilling outbound liquidity of a channel with the iTarget%. 

9. Now that you have things setup on a channel basis, you can review the global settings a bit and make sure things are to your liking. Lets look at each global setting and how to use it. 

10. AR-Enabled: This is used to turn the AR on and off. By setting this value to 1 you will allow LNDg to start scheduling rebalances based on your specifications. Think of this as a global on and off switch. 

11. AR-Target%: This specifies how big the rebalance attempts should be as a function of the channel capacity. This can be overridden in the advanced settings by setting a channel specific target amount. Updating this value will also update all specific channel target amounts. 

12. AR-Outbound%: This marks how full a channel must be in order to be considered to feed another channels during a rebalance attempt. This can be overridden as well in the advanced settings by setting a channel specific oTarget%. 

13. AR-MaxCost%: This lets LNDg know what % of the fees you charge on the enabled channel to put towards rebalancing that channel. If you charge 100 ppm out on an enabled channel with a 0.50 (50%) max cost. Then the max you will ever pay for this rebalance attempt will be 50 ppm. 

14. AR-Time: This determines how long we should search for a route before moving on to the next rebalance attempt. LNDg will not look again for 30 minutes after failing an attempt so try to keep things busy without making rebalances too long. Recommend staying around 3-5 mins. 

15. AR-MaxFeeRate: This is a fail safe to globally cap the max fee rates on any rebalance attempt. This cap will override the max cost % calculated value if it is lower. In our max cost example, a MaxFeeRate of 40 would have capped that rebalance down to 40 ppm instead of 50. 

16. AR-Autopilot: This setting will allow LNDg to automatically enable and disable channels based on the flow pattern of your node. This is a pretty great feature but go slow and try things out manually a bit before letting LNDg take over. This will help build more confidence. 

17. If you want to get an idea of what LNDg thinks you should be enabling or what would LNDg do if you were to turn on AR-Autopilot, then just head over to the Suggested AR Actions page (link right above channels table). If you see things here, this is what AP would do. 

18. If there are any channels you want to make sure are excluded from all rebalancing, you can either enable it and make sure the iTarget% is set to 100 or set the oTarget% to 100 as well if you want to keep it disabled. 

19. You should now be all set to fire things up! Go ahead and change the AR-Enabled value to 1 and start watching for rebalances to get scheduled by refreshing the page after a few moments. A new table should appear showing all the rebalances that LNDg has started to schedule. 

20. That's it! You are now on your way to maximizing your flow and potential earnings! 😎💪 
