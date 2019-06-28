namespace eval MPMStructure::write {
    variable mpm_project_parameters
    variable structure_project_parameters
}

proc MPMStructure::write::Init { } {
    variable mpm_project_parameters
    variable structure_project_parameters
    set mpm_project_parameters [dict create ]
    set structure_project_parameters [dict create ]
    
}

# Events
proc MPMStructure::write::writeModelPartEvent { } {
    variable mdpa_names
    set filename [Kratos::GetModelName]
    
    MPM::write::Init
    MPM::write::SetAttribute writeCoordinatesByGroups 1
    MPM::write::SetAttribute mpm_grid_extra_conditions [list LineMPMInterface2D LineMPMInterface2Da SurfaceMPMInterface3D]
    write::writeAppMDPA MPM
    set last_mpm_condition [MPM::write::GetLastConditionId]
    
    Structural::write::Init
    Structural::write::SetCoordinatesByGroups 1
    Structural::write::SetAttribute last_condition $last_mpm_condition
    Structural::write::RegisterCustomBlockMethod MPMStructure::write::CustomBlock
    write::writeAppMDPA Structural
    dict set mdpa_names Structural "${filename}_Structural"
    write::RenameFileInModel "$filename.mdpa" "[dict get $mdpa_names Structural].mdpa"
}

proc MPMStructure::write::writeCustomFilesEvent { } {
    Structural::write::WriteMaterialsFile
    MPM::write::WriteMaterialsFile
    
    # write::CopyFileIntoModel "python/KratosMPMStructure.py"
    # write::RenameFileInModel "KratosMPMStructure.py" "MainKratos.py"
}

proc MPMStructure::write::CustomBlock { } {
    # Time to write the interface Point condition
    set root [customlib::GetBaseRoot]
    if {$::Model::SpatialDimension eq "3D"} {
        set cnd SurfaceStructureInterface3D
        set nd 3
    } else {
        set cnd LineStructureInterface$Model::SpatialDimension
        set nd 2
    }
    set xp1 "[spdAux::getRoute [Structural::write::GetAttribute conditions_un]]/condition\[@n = '$cnd'\]/group"
    foreach group [$root selectNodes $xp1] {
        set groupid [$group @n]
        # Write the Condition block
        set intervals [write::writeGroupCondition $groupid PointLoadCondition${nd}D1N 1 [Structural::write::getLastConditionId]]
        dict set Structural::write::ConditionsDictGroupIterators $groupid $intervals
        # And the Submodelpart block
        GiD_Groups clone $groupid ${groupid}_pointelements
        ::write::writeGroupSubModelPart $cnd ${groupid}_pointelements "Conditions" $intervals
        GiD_Groups delete ${groupid}_pointelements
    }
}


MPMStructure::write::Init