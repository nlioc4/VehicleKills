"""
Simple script to track VehicleKills on a specific continent.
Allow options to specify user faction for coloured output and to track specific vehicle types.

Basic flow:
Auraxium event client, receive all VehicleKills events for given continent / server
Print events to console, colouring based on faction.
Display Timestamp Vehicle Name, Owner Name, Killer Name
Timestamp: {vehiclename}({somename}) killed by {someothername}

Second Column Displays estimated Nanites
Start Tracking players on first vehicle destroy event (attacker or victim)
Assume they start at 750 Nanites
Add 50 Nanites per minute
Subtract specific Nanites for vehicle type on death
Detect Current Vehicles via kills, remove on death
Display Nanites, along with colour code for level.  Green = 450+, Yellow = 300-450, Red = 0-300

Display Looks like:

Faction (NC) Tracking X Players
PlayerName: Estimated Nanites - Current Vehicle - Last Vehicle Death (type + time ago MM:SS)
_______________________________________________________________
list players here

Repeat for other factions


"""

import argparse
import asyncio
import sys
import auraxium
from rich.console import Console
from typing import Union
import datetime



#: Dictionary to retrieve faction name by id.
FACTIONS = {
    1: "VS",
    2: "NC",
    3: "TR",
    4: "NS"
}

#: Dictionary to retrieve faction ID by name.
FACTIONS_I = {v: k for k, v in FACTIONS.items()}

#: Faction colours for rich output.
FACTION_COLOURS = {
    0: "white",
    1: "magenta",
    2: "blue",
    3: "red",
    4: "grey"
}

#: Dictionary to retrieve zone name by id.
ZONES = {2: "Indar",
         4: "Hossin",
         6: "Amerish",
         8: "Esamir",
         344: "Oshur"}

#: Dictionary to retrieve zone ID by name.
ZONES_I = {v: k for k, v in ZONES.items()}

#: Dictionary to retrieve world name by ID.
WORLDS = {
    1: "Connery",
    10: "Miller",
    13: "Cobalt",
    17: "Emerald",
    19: "Jaeger",
    40: "SolTech"
}

#: Dictionary to retrieve world ID by name.
WORLDS_I = {v: k for k, v in WORLDS.items()}

#: Dictionary to retrieve vehicle name by id.
VEHICLES = {
    1: "Flash",
    2: "Sunderer",
    3: "Lightning",
    4: "Magrider",
    5: "Vanguard",
    6: "Prowler",
    7: "Scythe",
    8: "Reaver",
    9: "Mosquito",
    10: "Liberator",
    11: "Galaxy",
    12: "Harasser",
}

#: Dictionary to retrieve vehicle ID by name.
VEHICLES_I = {v: k for k, v in VEHICLES.items()}

#: Vehicle Colours for rich output.
VEHICLE_COLOUR = {
    # Light Ground Vehicles
    1: "orange4",
    2: "orange4",
    3: "orange4",
    12: "orange4",

    # Main Battle Tanks
    4: "cyan",
    5: "cyan",
    6: "cyan",

    # ESF's
    7: "green",
    8: "green",
    9: "green",

    # Large Aircraft
    10: "blue",
    11: "blue",
}


# Rich Console Object
CONS = Console()

# Character Cache.  Character ID -> Formatted Name
CHARS: dict[int: str] = {}
# TODO Update to store Nanites, last death event, current vehicle

# Auraxium Client
CLIENT: auraxium.EventClient | None = None


async def main():
    """Main Function"""

    # Parse Arguments
    ap = argparse.ArgumentParser(prog="Vehicle Tracker", description="Track Vehicle Kills on a specific continent")
    ap.add_argument("-i", "--service_id", type=str, required=True, help="Service ID for DBG API, with s: prefix")
    ap.add_argument("-c", "--continent", type=str, default="Indar", help="Continent to track", choices=ZONES_I.keys())
    ap.add_argument("-s", "--server", type=str, default="Jaeger", help="Server to track", choices=WORLDS_I.keys())
    ap.add_argument("-f", "--faction", type=str, required=False, help="User Team Faction", choices=FACTIONS_I.keys())
    args = vars(ap.parse_args())

    # Set up variables
    if (cont := args.get("continent")) and cont in ZONES_I:
        CONTINENT = ZONES_I.get(cont)
    else:
        sys.exit("Invalid Continent")

    if (serv := args.get("server")) and serv in WORLDS_I:
        SERVER = WORLDS_I.get(serv)
    else:
        sys.exit("Invalid Server")

    if (fac := args.get("faction")) and fac in FACTIONS_I:
        FACTION = FACTIONS_I.get(fac)
    else:
        FACTION = None

    # Print Header
    CONS.rule(f"Tracking Vehicle Kills on {ZONES.get(CONTINENT)} on {WORLDS.get(SERVER)}")

    # Set up Auraxium Client
    global CLIENT
    CLIENT = auraxium.EventClient(service_id=args.get('service_id'),
                                  ess_endpoint='wss://push.nanite-systems.net/streaming')

    # Define Trigger
    @CLIENT.trigger(auraxium.event.VehicleDestroy)
    async def destroy_handler(evt: Union[auraxium.event.VehicleDestroy, auraxium.event]):
        """Handles VehicleDestroy events.  Prints to console w/ colour and data"""
        # Check if right continent
        if evt.zone_id != CONTINENT or evt.world_id != SERVER:
            return

        # Check if teams faction
        good_faction = True if FACTION and evt.attacker_team_id == FACTION else False

        # Format timestamp
        timestamp = evt.timestamp.replace(tzinfo=datetime.timezone.utc).\
            astimezone(datetime.datetime.now().tzinfo).strftime("%H:%M:%S")
        # Check if Vehicle of Interest
        if not (vehicle := VEHICLES.get(evt.vehicle_id)):
            return

        # Format vehicle name
        vehicle = f'[{VEHICLE_COLOUR.get(evt.vehicle_id)}]{vehicle}[/{VEHICLE_COLOUR.get(evt.vehicle_id)}]'

        # Update character cache if required
        for char_id in (evt.attacker_character_id, evt.character_id):
            if char_id not in CHARS:
                char = await CLIENT.get_by_id(auraxium.ps2.Character, char_id)
                if not char:
                    continue
                faction_colour = FACTION_COLOURS.get(char.faction_id)
                CHARS[char_id] = f'[{faction_colour}]{char.name}[/{faction_colour}]'

        # Retrieve character names
        attacker = CHARS.get(evt.attacker_character_id, "Uncached Character")
        victim = CHARS.get(evt.character_id, "Uncached Character")

        # Print to console
        killed_by = "[underline]killed by[/underline]" if good_faction else "killed by"

        CONS.print(f'{timestamp}: {vehicle}({victim}) {killed_by} {attacker}', style='white')


if __name__ == '__main__':

    loop = asyncio.new_event_loop()
    try:

        main = loop.create_task(main())
        with CONS.status("Tracking..."):
            loop.run_forever()
    except KeyboardInterrupt:
        pass
    except SystemExit:
        pass
    finally:
        main.exception()
        CONS.print("[bright_red]Exiting...")
        if CLIENT:
            loop.run_until_complete(CLIENT.close())
