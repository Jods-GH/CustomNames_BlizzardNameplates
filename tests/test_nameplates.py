"""Behavior checks in Lua 5.1. Run: python -m unittest discover -s tests -v"""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "CustomNames_BlizzardNameplates.lua").read_text(encoding="utf-8")

HARNESS = r'''
units, plates, callbacks, eventFrames, hookCounts = {}, {}, {}, {}, {}
aliases, npcAliases = {}, {}
SECRET = {}
issecretvalue = function(v) return rawequal(v, SECRET) end
canaccessvalue = function(v) return not rawequal(v, SECRET) end
function UnitExists(unit) return units[unit] ~= nil end
function UnitName(unit)
    local u = units[unit]
    if u then return u.name, u.realm end
end
function UnitIsPlayer(unit) return units[unit].player end
lib = {}
function lib.UnitName(unit)
    local u = units[unit]
    return aliases[u.name .. '-' .. (u.realm or 'Home')] or u.name
end
function lib.GetCharList()
    local copy = {}
    for k,v in pairs(npcAliases) do copy[k] = v end
    return copy
end
function lib.RegisterCallback(owner, event, callback) callbacks[event] = callback end
function LibStub(name) assert(name == 'CustomNames'); return lib end
function CreateFrame()
    local frame = {events = {}}
    function frame:RegisterEvent(event) self.events[event] = true end
    function frame:SetScript(script, handler) self[script] = handler end
    eventFrames[#eventFrames + 1] = frame
    return frame
end
function fire(event, ...)
    for _, frame in ipairs(eventFrames) do
        if frame.events[event] then frame:OnEvent(event, ...) end
    end
end
function change(event) callbacks[event](event) end
function hooksecurefunc(target, method, callback)
    if type(target) == 'string' then callback, method, target = method, target, _G end
    local original = target[method]
    assert(type(original) == 'function')
    hookCounts[method] = (hookCounts[method] or 0) + 1
    target[method] = function(...)
        original(...)
        callback(...)
    end
end
function newFrame(unit)
    local text = { value = 'native', shown = true, writes = 0, color = 'class' }
    function text:GetText() return self.value end
    function text:SetText(value) self.value = value; self.writes = self.writes + 1 end
    function text:IsForbidden() return self.forbidden end
    local frame = {unit = unit, name = text}
    function frame:IsForbidden() return self.forbidden end
    return frame
end
function newPlate(unit, name, realm, player)
    units[unit] = {name = name, realm = realm, player = player}
    local plate = {UnitFrame = newFrame(unit)}
    function plate:IsForbidden() return self.forbidden end
    plates[unit] = plate
    return plate
end
function installUI()
    C_NamePlate = {}
    function C_NamePlate.GetNamePlateForUnit(unit, forbidden)
        assert(forbidden == nil, 'must not request forbidden plates')
        assert(type(unit) == 'string', 'secret token reached API')
        assert(not unit:match('^party%d') and not unit:match('^raid%d'),
            'Forever: party/raid tokens are not allowed')
        return plates[unit]
    end
    function C_NamePlate.GetNamePlates(forbidden)
        assert(forbidden == nil)
        local list = {}
        for _, plate in pairs(plates) do list[#list+1] = plate end
        return list
    end
    function CompactUnitFrame_UpdateName(frame)
        assert(not frame.forbidden, 'updated a forbidden frame')
        if frame.UpdateNameOverride then frame:UpdateNameOverride(); return end
        frame.name.shown = not frame.hideName
        if frame.hideName then return end
        local u = units[frame.unit]
        frame.name:SetText(u and (u.native or u.name))
    end
    NamePlateDriverFrame = {}
    function NamePlateDriverFrame:OnNamePlateAdded(unit)
        local plate = plates[unit]
        plate.UnitFrame = plate.UnitFrame or newFrame(unit)
        plate.UnitFrame.unit = unit
        CompactUnitFrame_UpdateName(plate.UnitFrame)
    end
end
installUI()
'''


class Nameplates(unittest.TestCase):
    def runtime(self, setup=""):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(HARNESS)
        lua.execute(setup)
        lua.execute(SOURCE)
        return lua

    def test_alias_add_edit_remove_restores_native_format(self):
        lua = self.runtime("p = newPlate('nameplate1', 'Alice', 'Away', true)")
        lua.execute("""
            units.nameplate1.native = 'Alice (*)'
            aliases['Alice-Away'] = 'Friend'; change('Name_Added')
            assert(p.UnitFrame.name.value == 'Friend')
            aliases['Alice-Away'] = 'Buddy'; change('Name_Update')
            assert(p.UnitFrame.name.value == 'Buddy')
            aliases['Alice-Away'] = nil; change('Name_Removed')
            assert(p.UnitFrame.name.value == 'Alice (*)')
        """)

    def test_classic_without_secret_apis(self):
        lua = self.runtime("""
            issecretvalue, canaccessvalue = nil, nil
            p = newPlate('nameplate1', 'Alice', nil, true)
            aliases['Alice-Home'] = 'Friend'
        """)
        lua.execute("assert(p.UnitFrame.name.value == 'Friend')")

    def test_forever_party_and_raid_updates_do_not_query_nameplates(self):
        lua = self.runtime("issecretvalue, canaccessvalue = nil, nil")
        lua.execute("""
            local lookups = 0
            local original = C_NamePlate.GetNamePlateForUnit
            C_NamePlate.GetNamePlateForUnit = function(...)
                lookups = lookups + 1
                return original(...)
            end
            for _, token in ipairs({'party1', 'party4', 'raid1', 'raid40',
                'partypet1', 'raidpet40', 'target', 'focus'}) do
                units[token] = {name = 'Alice', player = true}
                aliases['Alice-Home'] = 'Friend'
                local frame = newFrame(token)
                CompactUnitFrame_UpdateName(frame)
                fire('UNIT_NAME_UPDATE', token)
                assert(frame.name.value == 'Alice')
            end
            assert(lookups == 0)
            p = newPlate('nameplate1', 'Alice', nil, true)
            NamePlateDriverFrame:OnNamePlateAdded('nameplate1')
            assert(p.UnitFrame.name.value == 'Friend')
            assert(lookups > 0)
        """)

    def test_npc_and_pet_aliases(self):
        lua = self.runtime("p = newPlate('nameplate1', 'Wolf', nil, false)")
        lua.execute("""
            npcAliases.Wolf = 'Fluffy'; change('Name_Added')
            assert(p.UnitFrame.name.value == 'Fluffy')
            npcAliases.Wolf = nil; change('Name_Removed')
            assert(p.UnitFrame.name.value == 'Wolf')
        """)

    def test_library_normalization_and_inherited_aliases(self):
        lua = self.runtime("""
            p = newPlate('nameplate1', 'First Last', nil, true)
            lib.UnitName = function(unit) return 'Inherited BTag alias' end
        """)
        lua.execute("assert(p.UnitFrame.name.value == 'Inherited BTag alias')")

    def test_pool_reuse_and_detachment(self):
        lua = self.runtime("""
            p = newPlate('nameplate1', 'Alice', nil, true)
            aliases['Alice-Home'] = 'Friend'
        """)
        lua.execute("""
            local frame = p.UnitFrame
            plates.nameplate1, units.nameplate1 = nil, nil
            frame.unit = nil
            frame.name.value = 'released'; change('Name_Update')
            assert(frame.name.value == 'released')
            q = newPlate('nameplate2', 'Bob', nil, true)
            q.UnitFrame = frame
            NamePlateDriverFrame:OnNamePlateAdded('nameplate2')
            assert(frame.name.value == 'Bob')
            aliases['Bob-Home'] = 'Bobby'; change('Name_Added')
            assert(frame.name.value == 'Bobby')
            units.nameplate2.name = 'Charlie'
            fire('UNIT_NAME_UPDATE', 'nameplate2')
            assert(frame.name.value == 'Charlie')
        """)

    def test_name_updates_preserve_visibility_and_color(self):
        lua = self.runtime("""
            p = newPlate('nameplate1', 'Alice', nil, true)
            aliases['Alice-Home'] = 'Friend'
        """)
        lua.execute("""
            p.UnitFrame.hideName = true
            CompactUnitFrame_UpdateName(p.UnitFrame)
            assert(not p.UnitFrame.name.shown)
            assert(p.UnitFrame.name.color == 'class')
            p.UnitFrame.hideName = false
            CompactUnitFrame_UpdateName(p.UnitFrame)
            assert(p.UnitFrame.name.shown and p.UnitFrame.name.value == 'Friend')
        """)

    def test_ordinary_frames_and_previews_are_excluded(self):
        lua = self.runtime("""
            p = newPlate('nameplate1', 'Alice', nil, true)
            aliases['Alice-Home'] = 'Friend'
        """)
        lua.execute("""
            raid = newFrame('nameplate1')
            CompactUnitFrame_UpdateName(raid)
            assert(raid.name.value == 'Alice')
            units.player = units.nameplate1
            preview = newFrame('player')
            CompactUnitFrame_UpdateName(preview)
            assert(preview.name.value == 'Alice')
            p.UnitFrame.UpdateNameOverride = function(self) self.name:SetText('Override') end
            change('Name_Update')
            assert(p.UnitFrame.name.value == 'Override')
        """)

    def test_late_ui_load_and_hook_idempotence(self):
        lua = self.runtime("C_NamePlate, CompactUnitFrame_UpdateName, NamePlateDriverFrame = nil, nil, nil")
        lua.execute("""
            installUI()
            p = newPlate('nameplate1', 'Alice', nil, true)
            aliases['Alice-Home'] = 'Friend'
            fire('ADDON_LOADED', 'Blizzard_NamePlates')
            fire('PLAYER_LOGIN'); fire('PLAYER_ENTERING_WORLD')
            assert(p.UnitFrame.name.value == 'Friend')
            assert(hookCounts.CompactUnitFrame_UpdateName == 1)
            assert(hookCounts.OnNamePlateAdded == 1)
        """)

    def test_added_event_before_driver_initialization(self):
        lua = self.runtime()
        lua.execute("""
            p = newPlate('nameplate1', 'Alice', nil, true)
            p.UnitFrame = nil
            aliases['Alice-Home'] = 'Friend'
            fire('NAME_PLATE_UNIT_ADDED', 'nameplate1')
            NamePlateDriverFrame:OnNamePlateAdded('nameplate1')
            assert(p.UnitFrame.name.value == 'Friend')
        """)

    def test_forbidden_frames_and_regions(self):
        for field in ("p.forbidden", "p.UnitFrame.forbidden", "p.UnitFrame.name.forbidden"):
            with self.subTest(field=field):
                lua = self.runtime(f"""
                    p = newPlate('nameplate1', 'Alice', nil, true)
                    aliases['Alice-Home'] = 'Friend'
                    {field} = true
                """)
                lua.execute("assert(p.UnitFrame.name.value ~= 'Friend')")

    def test_restricted_values_keep_native_label(self):
        for restriction in (
            "units.nameplate1.name = SECRET",
            "units.nameplate1.realm = SECRET",
            "units.nameplate1.player = SECRET",
            "UnitExists = function() return SECRET end",
            "lib.UnitName = function() return SECRET end",
            "units.nameplate1.native = SECRET",
            "p.UnitFrame.unit = SECRET",
        ):
            with self.subTest(restriction=restriction):
                lua = self.runtime(f"""
                    p = newPlate('nameplate1', 'Alice', nil, true)
                    aliases['Alice-Home'] = 'Friend'
                    {restriction}
                """)
                lua.execute("assert(p.UnitFrame.name.value ~= 'Friend')")

    def test_canaccessvalue_without_issecretvalue(self):
        lua = self.runtime("""
            issecretvalue = nil
            p = newPlate('nameplate1', 'Alice', SECRET, true)
            aliases['Alice-Home'] = 'Friend'
        """)
        lua.execute("assert(p.UnitFrame.name.value == 'Alice')")

    def test_toc_loads_existing_files(self):
        toc = (ROOT / 'CustomNames_BlizzardNameplates.toc').read_text(encoding='utf-8')
        for line in toc.splitlines():
            if line.strip() and not line.startswith('#'):
                self.assertTrue((ROOT / line.strip()).is_file(), line)
        self.assertIn('RequiredDeps: CustomNames', toc)
        self.assertIn('CustomNames_BlizzardNameplates\\Media\\Logo.tga', toc)


if __name__ == '__main__':
    unittest.main()
