# fantasybaseball

This project consists of the `fantasybaseball` module that right now consists primarily
of a Fangraphs projections API.  In the future I plan to hook in additional resources
like FantasyPros, baseball reference, etc. (recommendations welcome!). I also plan to
add some real documentation but - seeing the 2021 season is upon us - decided I will 
push this as-is and see if anyone else is able to make use of the package for their 2021
drafts.  Importantly, this project also consists of the scripts `pull_projections.py`
and `generate_rankings.py` that allow you to pull down the latest projections
from Fangraphs and - based on your points-league scoring system - calculate projected 
fantasy points.  All you need to do is create a league .yaml file in the `leages` folder
with your league's scoring system, update `generate_rankings.py`, and you'll have custom
Fangraphs rankings!
