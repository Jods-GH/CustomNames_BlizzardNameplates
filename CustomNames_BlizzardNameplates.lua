local lib = LibStub("CustomNames")

local callbackOwner = {}
local nameHookInstalled = false
local hookedDrivers = setmetatable({}, { __mode = "k" })
local npcNames = {}

local function Readable(value)
    return not (issecretvalue and issecretvalue(value))
        and not (canaccessvalue and not canaccessvalue(value))
end

local function Usable(frame)
    return frame and not (frame.IsForbidden and frame:IsForbidden())
end

local function GetPlate(unit)
    if not Readable(unit) or type(unit) ~= "string" then return end
    -- Shared compact-frame hooks and UNIT_NAME_UPDATE also receive group tokens.
    -- Forever rejects party/raid tokens here instead of returning nil. Restrict
    -- lookups to nameplate tokens (plus the personal resource display's player).
    if unit ~= "player" and not unit:match("^nameplate%d+$") then return end
    if not C_NamePlate or not C_NamePlate.GetNamePlateForUnit then return end
    -- Do not request forbidden nameplates (the optional second argument).
    local plate = C_NamePlate.GetNamePlateForUnit(unit)
    if Usable(plate) then return plate end
end

local function IsNamePlate(frame)
    if not Usable(frame) then return false end
    local plate = GetPlate(frame.unit)
    -- CompactUnitFrame_UpdateName also updates party/raid frames. Only touch the
    -- actual Blizzard UnitFrame owned by a currently attached nameplate.
    return plate and plate.UnitFrame == frame
end

local function GetAlias(unit)
    local exists = UnitExists(unit)
    if not Readable(exists) or not exists then return end
    local name, realm = UnitName(unit)
    if not Readable(name) or not Readable(realm) or type(name) ~= "string" then return end
    local player = UnitIsPlayer(unit)
    if not Readable(player) then return end

    -- Let CustomNames handle realm/Forever normalization and inherited BTag names.
    -- On most clients Set(unit, alias) stores NPCs/pets under their bare name,
    -- whereas the library's UnitName getter normally appends a realm.
    local alias
    if not player then alias = npcNames[name] end
    if not Readable(alias) then return end
    if alias == nil then alias = lib.UnitName(unit) end
    if Readable(alias) and type(alias) == "string" and alias ~= name then
        return alias
    end
end

local function OnNameUpdated(frame)
    if not IsNamePlate(frame) or frame.UpdateNameOverride then return end
    local text = frame.name
    if not Usable(text) or not text.SetText or not text.GetText then return end
    -- A secret native label must remain Blizzard-owned even when other unit
    -- information happens to be available.
    if not Readable(text:GetText()) then return end
    local alias = GetAlias(frame.unit)
    if alias then text:SetText(alias) end
end

local function RefreshPlate(plate)
    if not nameHookInstalled or not Usable(plate) then return end
    local frame = plate.UnitFrame
    if IsNamePlate(frame) then
        -- Recompute the native label first, including realm formatting. This
        -- restores deleted aliases without caching text across pooled units.
        CompactUnitFrame_UpdateName(frame)
    end
end

local function RefreshUnit(unit)
    RefreshPlate(GetPlate(unit))
end

local function RefreshAll()
    if not C_NamePlate or not C_NamePlate.GetNamePlates then return end
    for _, plate in pairs(C_NamePlate.GetNamePlates()) do
        RefreshPlate(plate)
    end
end

local function InstallHooks()
    if not nameHookInstalled and type(CompactUnitFrame_UpdateName) == "function" then
        hooksecurefunc("CompactUnitFrame_UpdateName", OnNameUpdated)
        nameHookInstalled = true
    end
    local driver = NamePlateDriverFrame
    if Usable(driver) and not hookedDrivers[driver] and type(driver.OnNamePlateAdded) == "function" then
        -- Runs after Blizzard attaches/initializes the UnitFrame, regardless of
        -- event registration order. Supports both permanent and pooled frames.
        hooksecurefunc(driver, "OnNamePlateAdded", function(_, unit) RefreshUnit(unit) end)
        hookedDrivers[driver] = true
    end
end

local function NamesChanged()
    npcNames = lib.GetCharList()
    RefreshAll()
end

for _, event in ipairs({ "Name_Added", "Name_Update", "Name_Removed" }) do
    lib.RegisterCallback(callbackOwner, event, NamesChanged)
end

local events = CreateFrame("Frame")
for _, event in ipairs({ "ADDON_LOADED", "PLAYER_LOGIN", "PLAYER_ENTERING_WORLD", "NAME_PLATE_UNIT_ADDED", "UNIT_NAME_UPDATE" }) do
    events:RegisterEvent(event)
end
events:SetScript("OnEvent", function(_, event, unit)
    if event == "NAME_PLATE_UNIT_ADDED" or event == "UNIT_NAME_UPDATE" then
        RefreshUnit(unit)
    else
        -- Classic clients and Retail can load Blizzard's UI at different times.
        InstallHooks()
        NamesChanged()
    end
end)

InstallHooks()
NamesChanged()
