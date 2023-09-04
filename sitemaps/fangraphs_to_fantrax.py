import functools

import pandas as pd
import sys
import unicodedata


def normalize_name(name):
    name = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")
    name = name.replace(".", "")
    name = name.replace("Jr", "")
    name = name.strip()

    return str(name)


team_normalizations = {
    "WSH": "WSN",
    "SD": "SDP",
    "KC": "KCR",
    "TB": "TBR",
    "SF": "SFG",
    "(N/A)": "",
}


def normalize_team(team):
    if team in team_normalizations:
        team = team_normalizations[team]

    return team


def extract_position(index, position):
    position = position.replace(",", "/")
    positions = position.split("/")
    if index < len(positions):
        position = positions[index]
    else:
        position = ""

    return position


fantrax_file = sys.argv[1]
fangraphs_file = sys.argv[2]

fantrax_players = pd.read_csv(fantrax_file)
fantrax_players["NormName"] = fantrax_players["Player"].apply(normalize_name)
fantrax_players["NormTeam"] = fantrax_players["Team"].apply(normalize_team)
fantrax_players["Position1"] = fantrax_players["Position"].apply(functools.partial(extract_position, 0))
fantrax_players["Position2"] = fantrax_players["Position"].apply(functools.partial(extract_position, 1))
fantrax_players["Position3"] = fantrax_players["Position"].apply(functools.partial(extract_position, 2))
fantrax_players["Position4"] = fantrax_players["Position"].apply(functools.partial(extract_position, 3))

fangraphs_players = pd.read_csv(fangraphs_file).fillna("")
fangraphs_players["NormName"] = fangraphs_players["Name"].apply(normalize_name)

player_map = list()
skip_remaining = False
count = 0
for _, fantrax_player in fantrax_players.iterrows():
    count += 1
    fangraphs_player = dict()
    fangraphs_candidate_players = fangraphs_players[
        (fangraphs_players["NormName"] == fantrax_player["NormName"])
        & (fangraphs_players["Team"] == fantrax_player["NormTeam"])
        & (
            fangraphs_players["POS"].str.contains(fantrax_player["Position1"])
            | fangraphs_players["POS"].str.contains(fantrax_player["Position2"])
            | fangraphs_players["POS"].str.contains(fantrax_player["Position3"])
            | fangraphs_players["POS"].str.contains(fantrax_player["Position4"])
        )
    ]
    if fangraphs_candidate_players.shape[0] == 1:
        fangraphs_player = fangraphs_candidate_players.iloc[0].to_dict()
    elif not skip_remaining:
        if fangraphs_candidate_players.shape[0] == 0:
            fangraphs_candidate_players = fangraphs_players[fangraphs_players["NormName"] == fantrax_player["NormName"]]

        if fangraphs_candidate_players.shape[0] >= 1:
            while True:
                print("\033c", end="")
                print(f"Player {count} of {fantrax_players.shape[0]}.")
                print(f"Multiple fangraphs candidates for player:")
                print(fantrax_player.iloc[1:4])
                print()
                print(fangraphs_candidate_players.reset_index())
                print()
                candidate_id = input(
                    "Enter row number to select the candidate, leave empty to skip player, or enter -1 to stop: "
                )
                if not candidate_id:
                    print("Skipping.")
                    break
                try:
                    candidate_id = int(candidate_id.strip())
                    if candidate_id == -1:
                        print(f"Skipping remaining inputs...")
                        skip_remaining = True
                        break
                    if 0 <= candidate_id < fangraphs_candidate_players.shape[0]:
                        print(f"Selected candidate '{candidate_id}'.")
                        fangraphs_player = fangraphs_candidate_players.iloc[candidate_id].to_dict()
                        break
                except ValueError:
                    print(f"Invalid input: '{candidate_id}'")

    player_map_row = {
        "FantraxName": fantrax_player["Player"],
        "FantraxTeam": fantrax_player["Team"],
        "FantraxPosition": fantrax_player["Position"],
        "FantraxPlayerId": fantrax_player["ID"],
        "FangraphsName": fangraphs_player.get("Name"),
        "FangraphsTeam": fangraphs_player.get("Team"),
        "FangraphsPosition": fangraphs_player.get("POS"),
        "FangraphsPlayerId": fangraphs_player.get("PlayerId"),
    }
    player_map.append(player_map_row)

player_map = pd.DataFrame(player_map)
player_map.to_csv("fangraphs_to_fantrax.csv", index=False)
