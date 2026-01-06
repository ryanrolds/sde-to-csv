#!/usr/bin/env python3
"""
EVE Online SDE to CSV Converter

Converts the new JSON Lines SDE format to CSV files compatible with the old
Fuzzwork dump format.

CLI Usage:
    python convert.py <sde_path> [output_path]

Library Usage:
    from convert import convert_all, convert

    # Convert all files
    convert_all("sde/", "csv/")

    # Convert specific files
    convert("sde/", "csv/", only=["invTypes", "invGroups"])

    # List available converters
    from convert import CONVERTERS
    print(list(CONVERTERS.keys()))
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

__all__ = ["convert_all", "convert", "CONVERTERS", "SDEConverter"]


class SDEConverter:
    """Base converter for SDE JSON Lines to CSV."""

    def __init__(self, sde_path: Path, output_path: Path, quiet: bool = False):
        self.sde_path = Path(sde_path)
        self.output_path = Path(output_path)
        self.quiet = quiet
        self.output_path.mkdir(parents=True, exist_ok=True)

    def read_jsonl(self, filename: str):
        """Read a JSONL file and yield parsed objects."""
        filepath = self.sde_path / filename
        if not filepath.exists():
            if not self.quiet:
                print(f"Warning: {filepath} not found, skipping")
            return
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                yield json.loads(line)

    def write_csv(self, filename: str, columns: list[str], rows: list[dict]):
        """Write rows to a CSV file."""
        filepath = self.output_path / filename
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        if not self.quiet:
            print(f"Wrote {len(rows)} rows to {filepath}")

    def get_localized(self, obj: dict, field: str, lang: str = "en") -> str | None:
        """Extract localized string from nested dict."""
        value = obj.get(field)
        if value is None:
            return None
        if isinstance(value, dict):
            return value.get(lang)
        return value

    def convert_value(self, value: Any) -> Any:
        """Convert a value for CSV output."""
        if value is None:
            return None
        if isinstance(value, bool):
            return 1 if value else 0
        return value


class InvTypesConverter(SDEConverter):
    """Convert types.jsonl to invTypes.csv"""

    COLUMNS = [
        "typeID",
        "groupID",
        "typeName",
        "description",
        "mass",
        "volume",
        "capacity",
        "portionSize",
        "raceID",
        "basePrice",
        "published",
        "marketGroupID",
        "iconID",
        "soundID",
        "graphicID",
    ]

    def convert(self):
        rows = []
        for obj in self.read_jsonl("types.jsonl"):
            row = {
                "typeID": obj.get("_key"),
                "groupID": obj.get("groupID"),
                "typeName": self.get_localized(obj, "name"),
                "description": self.get_localized(obj, "description"),
                "mass": obj.get("mass"),
                "volume": obj.get("volume"),
                "capacity": obj.get("capacity"),
                "portionSize": obj.get("portionSize"),
                "raceID": obj.get("raceID"),
                "basePrice": obj.get("basePrice"),
                "published": self.convert_value(obj.get("published")),
                "marketGroupID": obj.get("marketGroupID"),
                "iconID": obj.get("iconID"),
                "soundID": obj.get("soundID"),
                "graphicID": obj.get("graphicID"),
            }
            rows.append(row)
        self.write_csv("invTypes.csv", self.COLUMNS, rows)


class InvGroupsConverter(SDEConverter):
    """Convert groups.jsonl to invGroups.csv"""

    COLUMNS = [
        "groupID",
        "categoryID",
        "groupName",
        "iconID",
        "useBasePrice",
        "anchored",
        "anchorable",
        "fittableNonSingleton",
        "published",
    ]

    def convert(self):
        rows = []
        for obj in self.read_jsonl("groups.jsonl"):
            row = {
                "groupID": obj.get("_key"),
                "categoryID": obj.get("categoryID"),
                "groupName": self.get_localized(obj, "name"),
                "iconID": obj.get("iconID"),
                "useBasePrice": self.convert_value(obj.get("useBasePrice")),
                "anchored": self.convert_value(obj.get("anchored")),
                "anchorable": self.convert_value(obj.get("anchorable")),
                "fittableNonSingleton": self.convert_value(obj.get("fittableNonSingleton")),
                "published": self.convert_value(obj.get("published")),
            }
            rows.append(row)
        self.write_csv("invGroups.csv", self.COLUMNS, rows)


class InvMetaGroupsConverter(SDEConverter):
    """Convert metaGroups.jsonl to invMetaGroups.csv"""

    COLUMNS = ["metaGroupID", "metaGroupName", "description", "iconID"]

    def convert(self):
        rows = []
        for obj in self.read_jsonl("metaGroups.jsonl"):
            row = {
                "metaGroupID": obj.get("_key"),
                "metaGroupName": self.get_localized(obj, "name"),
                "description": self.get_localized(obj, "description"),
                "iconID": obj.get("iconID"),
            }
            rows.append(row)
        self.write_csv("invMetaGroups.csv", self.COLUMNS, rows)


class InvMetaTypesConverter(SDEConverter):
    """Convert types.jsonl to invMetaTypes.csv (meta group relationships)"""

    COLUMNS = ["typeID", "parentTypeID", "metaGroupID"]

    def convert(self):
        rows = []
        for obj in self.read_jsonl("types.jsonl"):
            meta_group_id = obj.get("metaGroupID")
            if meta_group_id is not None:
                row = {
                    "typeID": obj.get("_key"),
                    "parentTypeID": obj.get("variationParentTypeID"),
                    "metaGroupID": meta_group_id,
                }
                rows.append(row)
        self.write_csv("invMetaTypes.csv", self.COLUMNS, rows)


class IndustryActivityConverter(SDEConverter):
    """Convert blueprints.jsonl to industryActivity.csv"""

    COLUMNS = ["typeID", "activityID", "time"]

    # Map activity names to IDs
    ACTIVITY_IDS = {
        "manufacturing": 1,
        "research_time": 3,
        "research_material": 4,
        "copying": 5,
        "invention": 8,
        "reaction": 11,
    }

    def convert(self):
        rows = []
        for obj in self.read_jsonl("blueprints.jsonl"):
            blueprint_id = obj.get("blueprintTypeID")
            activities = obj.get("activities", {})
            for activity_name, activity_data in activities.items():
                activity_id = self.ACTIVITY_IDS.get(activity_name)
                if activity_id is not None and "time" in activity_data:
                    row = {
                        "typeID": blueprint_id,
                        "activityID": activity_id,
                        "time": activity_data["time"],
                    }
                    rows.append(row)
        self.write_csv("industryActivity.csv", self.COLUMNS, rows)


class IndustryActivityMaterialsConverter(SDEConverter):
    """Convert blueprints.jsonl to industryActivityMaterials.csv"""

    COLUMNS = ["typeID", "activityID", "materialTypeID", "quantity"]

    ACTIVITY_IDS = {
        "manufacturing": 1,
        "research_time": 3,
        "research_material": 4,
        "copying": 5,
        "invention": 8,
        "reaction": 11,
    }

    def convert(self):
        rows = []
        for obj in self.read_jsonl("blueprints.jsonl"):
            blueprint_id = obj.get("blueprintTypeID")
            activities = obj.get("activities", {})
            for activity_name, activity_data in activities.items():
                activity_id = self.ACTIVITY_IDS.get(activity_name)
                if activity_id is not None:
                    for material in activity_data.get("materials", []):
                        row = {
                            "typeID": blueprint_id,
                            "activityID": activity_id,
                            "materialTypeID": material.get("typeID"),
                            "quantity": material.get("quantity"),
                        }
                        rows.append(row)
        self.write_csv("industryActivityMaterials.csv", self.COLUMNS, rows)


class IndustryActivityProductsConverter(SDEConverter):
    """Convert blueprints.jsonl to industryActivityProducts.csv"""

    COLUMNS = ["typeID", "activityID", "productTypeID", "quantity"]

    ACTIVITY_IDS = {
        "manufacturing": 1,
        "research_time": 3,
        "research_material": 4,
        "copying": 5,
        "invention": 8,
        "reaction": 11,
    }

    def convert(self):
        rows = []
        for obj in self.read_jsonl("blueprints.jsonl"):
            blueprint_id = obj.get("blueprintTypeID")
            activities = obj.get("activities", {})
            for activity_name, activity_data in activities.items():
                activity_id = self.ACTIVITY_IDS.get(activity_name)
                if activity_id is not None:
                    for product in activity_data.get("products", []):
                        row = {
                            "typeID": blueprint_id,
                            "activityID": activity_id,
                            "productTypeID": product.get("typeID"),
                            "quantity": product.get("quantity"),
                        }
                        rows.append(row)
        self.write_csv("industryActivityProducts.csv", self.COLUMNS, rows)


class RamActivitiesConverter(SDEConverter):
    """Generate ramActivities.csv (static reference data)"""

    COLUMNS = ["activityID", "activityName", "iconNo", "description", "published"]

    ACTIVITIES = [
        (0, "None", None, "No activity", 1),
        (1, "Manufacturing", "18_02", None, 1),
        (3, "Researching Time Efficiency", "33_02", None, 1),
        (4, "Researching Material Efficiency", "33_02", None, 1),
        (5, "Copying", "33_02", None, 1),
        (8, "Invention", "33_02", None, 1),
        (11, "Reactions", "18_02", None, 1),
    ]

    def convert(self):
        rows = []
        for activity_id, name, icon, desc, published in self.ACTIVITIES:
            row = {
                "activityID": activity_id,
                "activityName": name,
                "iconNo": icon,
                "description": desc,
                "published": published,
            }
            rows.append(row)
        self.write_csv("ramActivities.csv", self.COLUMNS, rows)


class InvFlagsConverter(SDEConverter):
    """Generate invFlags.csv (static reference data for inventory locations)"""

    COLUMNS = ["flagID", "flagName", "flagText", "orderID"]

    # Static flag definitions (from EVE database)
    FLAGS = [
        (0, "None", "None", 0),
        (1, "Wallet", "Wallet", 10),
        (2, "Offices", "OfficeFolder", 0),
        (3, "Wardrobe", "Wardrobe", 0),
        (4, "Hangar", "Hangar", 30),
        (5, "Cargo", "Cargo", 3000),
        (6, "OfficeImpound", "Impounded Offices", 0),
        (7, "Skill", "Skill", 15),
        (8, "Reward", "Reward", 17),
        (11, "LoSlot0", "Low power slot 1", 0),
        (12, "LoSlot1", "Low power slot 2", 0),
        (13, "LoSlot2", "Low power slot 3", 0),
        (14, "LoSlot3", "Low power slot 4", 0),
        (15, "LoSlot4", "Low power slot 5", 0),
        (16, "LoSlot5", "Low power slot 6", 0),
        (17, "LoSlot6", "Low power slot 7", 0),
        (18, "LoSlot7", "Low power slot 8", 0),
        (19, "MedSlot0", "Medium power slot 1", 0),
        (20, "MedSlot1", "Medium power slot 2", 0),
        (21, "MedSlot2", "Medium power slot 3", 0),
        (22, "MedSlot3", "Medium power slot 4", 0),
        (23, "MedSlot4", "Medium power slot 5", 0),
        (24, "MedSlot5", "Medium power slot 6", 0),
        (25, "MedSlot6", "Medium power slot 7", 0),
        (26, "MedSlot7", "Medium power slot 8", 0),
        (27, "HiSlot0", "High power slot 1", 0),
        (28, "HiSlot1", "High power slot 2", 0),
        (29, "HiSlot2", "High power slot 3", 0),
        (30, "HiSlot3", "High power slot 4", 0),
        (31, "HiSlot4", "High power slot 5", 0),
        (32, "HiSlot5", "High power slot 6", 0),
        (33, "HiSlot6", "High power slot 7", 0),
        (34, "HiSlot7", "High power slot 8", 0),
        (35, "Fixed Slot", "Fixed Slot", 0),
        (36, "AssetSafety", "Asset Safety", 0),
        (56, "Capsule", "Capsule", 0),
        (57, "Pilot", "Pilot", 0),
        (61, "Skill In Training", "Skill in training", 0),
        (62, "CorpMarket", "Corporation Market Deliveries / Returns", 0),
        (63, "Locked", "Locked item, can not be moved unless unlocked", 0),
        (64, "Unlocked", "Unlocked item, can be moved", 0),
        (70, "Office Slot 1", "Office slot 1", 0),
        (71, "Office Slot 2", "Office slot 2", 0),
        (72, "Office Slot 3", "Office slot 3", 0),
        (73, "Office Slot 4", "Office slot 4", 0),
        (74, "Office Slot 5", "Office slot 5", 0),
        (75, "Office Slot 6", "Office slot 6", 0),
        (76, "Office Slot 7", "Office slot 7", 0),
        (77, "Office Slot 8", "Office slot 8", 0),
        (78, "Office Slot 9", "Office slot 9", 0),
        (79, "Office Slot 10", "Office slot 10", 0),
        (80, "Office Slot 11", "Office slot 11", 0),
        (81, "Office Slot 12", "Office slot 12", 0),
        (82, "Office Slot 13", "Office slot 13", 0),
        (83, "Office Slot 14", "Office slot 14", 0),
        (84, "Office Slot 15", "Office slot 15", 0),
        (85, "Office Slot 16", "Office slot 16", 0),
        (86, "Bonus", "Bonus", 0),
        (87, "DroneBay", "Drone Bay", 0),
        (88, "Booster", "Booster", 0),
        (89, "Implant", "Implant", 0),
        (90, "ShipHangar", "Ship Hangar", 0),
        (91, "ShipOffline", "Ship Offline", 0),
        (92, "RigSlot0", "Rig power slot 1", 0),
        (93, "RigSlot1", "Rig power slot 2", 0),
        (94, "RigSlot2", "Rig power slot 3", 0),
        (95, "RigSlot3", "Rig power slot 4", 0),
        (96, "RigSlot4", "Rig power slot 5", 0),
        (97, "RigSlot5", "Rig power slot 6", 0),
        (98, "RigSlot6", "Rig power slot 7", 0),
        (99, "RigSlot7", "Rig power slot 8", 0),
        (115, "CorpSAG1", "Corp Security Access Group 1", 0),
        (116, "CorpSAG2", "Corp Security Access Group 2", 0),
        (117, "CorpSAG3", "Corp Security Access Group 3", 0),
        (118, "CorpSAG4", "Corp Security Access Group 4", 0),
        (119, "CorpSAG5", "Corp Security Access Group 5", 0),
        (120, "CorpSAG6", "Corp Security Access Group 6", 0),
        (121, "CorpSAG7", "Corp Security Access Group 7", 0),
        (122, "SecondaryStorage", "Secondary Storage", 0),
        (125, "SubSystem0", "Sub system slot 0", 0),
        (126, "SubSystem1", "Sub system slot 1", 0),
        (127, "SubSystem2", "Sub system slot 2", 0),
        (128, "SubSystem3", "Sub system slot 3", 0),
        (129, "SubSystem4", "Sub system slot 4", 0),
        (130, "SubSystem5", "Sub system slot 5", 0),
        (131, "SubSystem6", "Sub system slot 6", 0),
        (132, "SubSystem7", "Sub system slot 7", 0),
        (133, "SpecializedFuelBay", "Specialized Fuel Bay", 0),
        (134, "SpecializedAsteroidHold", "Specialized Asteroid Hold", 0),
        (135, "SpecializedGasHold", "Specialized Gas Hold", 0),
        (136, "SpecializedMineralHold", "Specialized Mineral Hold", 0),
        (137, "SpecializedSalvageHold", "Specialized Salvage Hold", 0),
        (138, "SpecializedShipHold", "Specialized Ship Hold", 0),
        (139, "SpecializedSmallShipHold", "Specialized Small Ship Hold", 0),
        (140, "SpecializedMediumShipHold", "Specialized Medium Ship Hold", 0),
        (141, "SpecializedLargeShipHold", "Specialized Large Ship Hold", 0),
        (142, "SpecializedIndustrialShipHold", "Specialized Industrial Ship Hold", 0),
        (143, "SpecializedAmmoHold", "Specialized Ammo Hold", 0),
        (144, "StructureActive", "Structure Active", 0),
        (145, "StructureInactive", "Structure Inactive", 0),
        (146, "JunkyardReprocessed", "This item was put into a junkyard through reprocession.", 0),
        (147, "JunkyardTrashed", "This item was put into a junkyard through being trashed by its owner.", 0),
        (148, "SpecializedCommandCenterHold", "Specialized Command Center Hold", 0),
        (149, "SpecializedPlanetaryCommoditiesHold", "Specialized Planetary Commodities Hold", 0),
        (150, "PlanetSurface", "Planet Surface", 0),
        (151, "SpecializedMaterialBay", "Specialized Material Bay", 0),
        (152, "DustCharacterDatabank", "Dust Character Databank", 0),
        (153, "DustCharacterBattle", "Dust Character Battle", 0),
        (154, "QuafeBay", "Quafe Bay", 0),
        (155, "FleetHangar", "Fleet Hangar", 0),
        (156, "HiddenModifiers", "Hidden Modifiers", 0),
        (157, "StructureOffline", "Structure Offline", 0),
        (158, "FighterBay", "Fighter Bay", 0),
        (159, "FighterTube0", "Fighter Tube 0", 0),
        (160, "FighterTube1", "Fighter Tube 1", 0),
        (161, "FighterTube2", "Fighter Tube 2", 0),
        (162, "FighterTube3", "Fighter Tube 3", 0),
        (163, "FighterTube4", "Fighter Tube 4", 0),
        (164, "StructureServiceSlot0", "Structure service slot 1", 0),
        (165, "StructureServiceSlot1", "Structure service slot 2", 0),
        (166, "StructureServiceSlot2", "Structure service slot 3", 0),
        (167, "StructureServiceSlot3", "Structure service slot 4", 0),
        (168, "StructureServiceSlot4", "Structure service slot 5", 0),
        (169, "StructureServiceSlot5", "Structure service slot 6", 0),
        (170, "StructureServiceSlot6", "Structure service slot 7", 0),
        (171, "StructureServiceSlot7", "Structure service slot 8", 0),
        (172, "StructureFuel", "Structure Fuel", 0),
        (173, "Deliveries", "Deliveries", 0),
        (174, "CrateLoot", "Crate Loot", 0),
        (176, "BoosterBay", "Booster Hold", 0),
        (177, "SubsystemBay", "Subsystem Hold", 0),
        (178, "Raffles", "Raffles Hangar", 0),
        (179, "FrigateEscapeBay", "Frigate escape bay Hangar", 0),
        (180, "StructureDeedBay", "Structure Deed Bay", 0),
        (181, "SpecializedIceHold", "Specialized Ice Hold", 0),
        (182, "SpecializedAsteroidHold", "Specialized Asteroid Hold", 0),
        (183, "MobileDepot", "Mobile Depot", 0),
        (184, "CorpProjectsHangar", "Corporation Projects Hangar ", 0),
        (185, "ColonyResourcesHold", "Infrastructure Hold", 0),
        (186, "MoonMaterialBay", "Moon Material Bay", 0),
        (187, "CapsuleerDeliveries", "Capsuleer Deliveries", 0),
    ]

    def convert(self):
        rows = []
        for flag_id, name, text, order in self.FLAGS:
            row = {
                "flagID": flag_id,
                "flagName": name,
                "flagText": text,
                "orderID": order,
            }
            rows.append(row)
        self.write_csv("invFlags.csv", self.COLUMNS, rows)


class InvUniqueNamesConverter(SDEConverter):
    """Convert npcCharacters.jsonl to invUniqueNames.csv"""

    COLUMNS = ["itemID", "itemName", "groupID"]

    def convert(self):
        rows = []
        # NPC Characters have groupID 1 (Character group)
        for obj in self.read_jsonl("npcCharacters.jsonl"):
            row = {
                "itemID": obj.get("_key"),
                "itemName": self.get_localized(obj, "name"),
                "groupID": 1,  # Character group
            }
            rows.append(row)
        self.write_csv("invUniqueNames.csv", self.COLUMNS, rows)


class InvNamesConverter(SDEConverter):
    """Generate invNames.csv from multiple SDE sources."""

    COLUMNS = ["itemID", "itemName"]

    ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
             "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]

    def convert(self):
        rows = []

        # Build lookup tables
        solar_systems = {}  # id -> name
        for obj in self.read_jsonl("mapSolarSystems.jsonl"):
            solar_systems[obj["_key"]] = self.get_localized(obj, "name")
            rows.append({"itemID": obj["_key"], "itemName": self.get_localized(obj, "name")})

        planets = {}  # id -> (solarSystemID, celestialIndex)
        for obj in self.read_jsonl("mapPlanets.jsonl"):
            planet_id = obj["_key"]
            solar_id = obj.get("solarSystemID") or self._get_solar_from_orbit(obj, solar_systems)
            celestial_idx = obj.get("celestialIndex", 0)
            planets[planet_id] = (solar_id, celestial_idx)

            sys_name = solar_systems.get(solar_id, "Unknown")
            roman = self.ROMAN[celestial_idx] if celestial_idx < len(self.ROMAN) else str(celestial_idx)
            rows.append({"itemID": planet_id, "itemName": f"{sys_name} {roman}"})

        # Moons
        for obj in self.read_jsonl("mapMoons.jsonl"):
            moon_id = obj["_key"]
            orbit_id = obj.get("orbitID")
            orbit_idx = obj.get("orbitIndex", 1)
            solar_id = obj.get("solarSystemID")
            sys_name = solar_systems.get(solar_id, "Unknown")

            if orbit_id in planets:
                _, celestial_idx = planets[orbit_id]
                roman = self.ROMAN[celestial_idx] if celestial_idx < len(self.ROMAN) else str(celestial_idx)
                rows.append({"itemID": moon_id, "itemName": f"{sys_name} {roman} - Moon {orbit_idx}"})
            else:
                rows.append({"itemID": moon_id, "itemName": f"{sys_name} - Moon {orbit_idx}"})

        # Stars (same name as solar system)
        for obj in self.read_jsonl("mapStars.jsonl"):
            star_id = obj["_key"]
            solar_id = obj.get("solarSystemID")
            sys_name = solar_systems.get(solar_id, "Unknown")
            rows.append({"itemID": star_id, "itemName": f"{sys_name} - Star"})

        # Regions
        for obj in self.read_jsonl("mapRegions.jsonl"):
            rows.append({"itemID": obj["_key"], "itemName": self.get_localized(obj, "name")})

        # Constellations
        for obj in self.read_jsonl("mapConstellations.jsonl"):
            rows.append({"itemID": obj["_key"], "itemName": self.get_localized(obj, "name")})

        # Corporations
        for obj in self.read_jsonl("npcCorporations.jsonl"):
            rows.append({"itemID": obj["_key"], "itemName": self.get_localized(obj, "name")})

        # Factions
        for obj in self.read_jsonl("factions.jsonl"):
            rows.append({"itemID": obj["_key"], "itemName": self.get_localized(obj, "name")})

        # NPC Characters
        for obj in self.read_jsonl("npcCharacters.jsonl"):
            rows.append({"itemID": obj["_key"], "itemName": self.get_localized(obj, "name")})

        self.write_csv("invNames.csv", self.COLUMNS, rows)

    def _get_solar_from_orbit(self, obj, solar_systems):
        """Try to determine solar system from orbit chain."""
        orbit_id = obj.get("orbitID")
        if orbit_id and orbit_id in solar_systems:
            return orbit_id
        return None


class InvItemsConverter(SDEConverter):
    """Generate invItems.csv from SDE sources."""

    COLUMNS = ["itemID", "typeID", "ownerID", "locationID", "flagID", "quantity"]

    def convert(self):
        rows = []

        # Solar systems (typeID 5 = Solar System)
        for obj in self.read_jsonl("mapSolarSystems.jsonl"):
            region_id = obj.get("regionID", 0)
            rows.append({
                "itemID": obj["_key"],
                "typeID": 5,
                "ownerID": 1,
                "locationID": region_id,
                "flagID": 0,
                "quantity": -1,
            })

        # Planets
        for obj in self.read_jsonl("mapPlanets.jsonl"):
            solar_id = obj.get("solarSystemID", 0)
            type_id = obj.get("typeID", 0)
            rows.append({
                "itemID": obj["_key"],
                "typeID": type_id,
                "ownerID": 1,
                "locationID": solar_id,
                "flagID": 0,
                "quantity": -1,
            })

        # Moons
        for obj in self.read_jsonl("mapMoons.jsonl"):
            solar_id = obj.get("solarSystemID", 0)
            type_id = obj.get("typeID", 0)
            rows.append({
                "itemID": obj["_key"],
                "typeID": type_id,
                "ownerID": 1,
                "locationID": solar_id,
                "flagID": 0,
                "quantity": -1,
            })

        # NPC Stations
        for obj in self.read_jsonl("npcStations.jsonl"):
            solar_id = obj.get("solarSystemID", 0)
            type_id = obj.get("typeID", 0)
            owner_id = obj.get("ownerID", 0)
            rows.append({
                "itemID": obj["_key"],
                "typeID": type_id,
                "ownerID": owner_id,
                "locationID": solar_id,
                "flagID": 0,
                "quantity": -1,
            })

        self.write_csv("invItems.csv", self.COLUMNS, rows)


# Registry of all converters
CONVERTERS: dict[str, type[SDEConverter]] = {
    "invTypes": InvTypesConverter,
    "invGroups": InvGroupsConverter,
    "invMetaGroups": InvMetaGroupsConverter,
    "invMetaTypes": InvMetaTypesConverter,
    "industryActivity": IndustryActivityConverter,
    "industryActivityMaterials": IndustryActivityMaterialsConverter,
    "industryActivityProducts": IndustryActivityProductsConverter,
    "ramActivities": RamActivitiesConverter,
    "invFlags": InvFlagsConverter,
    "invUniqueNames": InvUniqueNamesConverter,
    "invNames": InvNamesConverter,
    "invItems": InvItemsConverter,
}


def convert(
    sde_path: str | Path,
    output_path: str | Path = "csv",
    only: list[str] | None = None,
    quiet: bool = False,
) -> None:
    """
    Convert SDE JSON Lines files to CSV.

    Args:
        sde_path: Path to directory containing SDE JSONL files
        output_path: Output directory for CSV files (default: "csv")
        only: List of specific converters to run (default: all)
        quiet: Suppress output messages

    Example:
        convert("sde/", "csv/", only=["invTypes", "invGroups"])
    """
    sde_path = Path(sde_path)
    output_path = Path(output_path)

    if not sde_path.exists():
        raise FileNotFoundError(f"SDE path {sde_path} does not exist")

    converters_to_run = only if only else list(CONVERTERS.keys())

    for name in converters_to_run:
        if name not in CONVERTERS:
            raise ValueError(f"Unknown converter: {name}")
        converter_class = CONVERTERS[name]
        converter = converter_class(sde_path, output_path, quiet=quiet)
        if not quiet:
            print(f"Converting {name}...")
        converter.convert()

    if not quiet:
        print("Done!")


def convert_all(
    sde_path: str | Path,
    output_path: str | Path = "csv",
    quiet: bool = False,
) -> None:
    """
    Convert all SDE JSON Lines files to CSV.

    Args:
        sde_path: Path to directory containing SDE JSONL files
        output_path: Output directory for CSV files (default: "csv")
        quiet: Suppress output messages

    Example:
        convert_all("sde/", "csv/")
    """
    convert(sde_path, output_path, only=None, quiet=quiet)


def main():
    parser = argparse.ArgumentParser(
        description="Convert EVE Online SDE JSON Lines to CSV"
    )
    parser.add_argument("sde_path", type=Path, help="Path to SDE JSONL files")
    parser.add_argument(
        "output_path",
        type=Path,
        nargs="?",
        default=Path("csv"),
        help="Output directory for CSV files (default: csv)",
    )
    parser.add_argument(
        "--only",
        type=str,
        nargs="+",
        choices=list(CONVERTERS.keys()),
        help="Only convert specific files",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress output messages",
    )

    args = parser.parse_args()

    try:
        convert(args.sde_path, args.output_path, only=args.only, quiet=args.quiet)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
