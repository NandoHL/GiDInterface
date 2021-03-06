
proc Kratos::Quicktest {example_app example_dim example_cmd} {
    apps::setActiveApp Examples
    ::Examples::LaunchExample $example_app $example_dim $example_cmd
} 

proc Kratos::ForceRun { } {
    # validated by escolano@cimne.upc.edu
    variable must_write_calc_data
    set temp $must_write_calc_data
    set must_write_calc_data 0
    GiD_Process Mescape Utilities Calculate escape escape
    set must_write_calc_data $temp
}

proc Kratos::DestroyWindows { } {
    gid_groups_conds::close_all_windows
    spdAux::DestroyWindow
    if {[info exists ::Kratos::kratos_private(UseWizard)] && $::Kratos::kratos_private(UseWizard)} {
        smart_wizard::DestroyWindow
    }
    ::Kratos::EndCreatePreprocessTBar
}

proc Kratos::ResetModel { } {
    foreach layer [GiD_Info layers] {
        GiD_Process 'Layers Delete $layer Yes escape escape
    }
    foreach group [GiD_Groups list] {
        if {[GiD_Groups exists $group]} {GiD_Groups delete $group}
    }
}

proc Kratos::GetModelName { } {
    return [file tail [GiD_Info project ModelName]]
}

proc Kratos::IsModelEmpty { } {
    if {[GiD_Groups list] != ""} {return false}
    if {[GiD_Layers list] != "Layer0"} {return false}
    if {[GiD_Geometry list point 1:end] != ""} {return false}
    return true
}

proc Kratos::CheckValidProjectName {modelname} {
    set fail 0
    set filename [file tail $modelname]
    if {[string is double $filename]} {set fail 1}
    if {[write::isBoolean $filename]} {set fail 1}
    if {$filename == "null"} {set fail 1}
    return $fail
}

proc Kratos::PrintArray {a {pattern *}} {
    upvar 1 $a array  
    if {![array exists array]} {
        error "\"$a\" isn't an array"
    }
    set maxl 0
    foreach name [lsort [array names array $pattern]] {
        if {[string length $name] > $maxl} {
            set maxl [string length $name]
        }
    }
    set maxl [expr {$maxl + [string length $a] + 2}]
    foreach name [lsort [array names array $pattern]] {
        set nameString [format %s(%s) $a $name]
        W "[format "%-*s = %s" $maxl $nameString $array($name)]"
    }
}

proc Kratos::CheckProjectIsNew {filespd} {
    variable kratos_private
    set filedir [file dirname $filespd]
    if {[file nativename $kratos_private(Path)] eq [file nativename $filedir]} {
        set kratos_private(ProjectIsNew) 1
    } else {
        set kratos_private(ProjectIsNew) 0
    }
}


proc Kratos::WarnAboutMinimumRecommendedGiDVersion { } {
    variable kratos_private

    if { [GidUtils::VersionCmp $kratos_private(CheckMinimumGiDVersion)] < 0 } {
        W "Warning: kratos interface requires GiD $kratos_private(CheckMinimumGiDVersion) or later."
        if { [GidUtils::VersionCmp 14.0.0] < 0 } {
            W "If you are still using a GiD version 13.1.7d or later, you can still use most of the features, but think about upgrading to GiD 14." 
        } {
            W "If you are using an official version of GiD 14, we recommend to use the latest developer version"
        }
        W "Download it from: https://www.gidhome.com/download/developer-versions/"
    }
}

# Customlib libs and preferences
proc Kratos::LoadProblemtypeLibraries {} {  
    package require customlib_extras
    package require customlib_native_groups
    variable kratos_private
    
    gid_groups_conds::SetProgramName $kratos_private(Name)
    gid_groups_conds::SetLibDir [file join $kratos_private(Path) exec]
    set spdfile [file join $kratos_private(Path) kratos_default.spd]
    if {[llength [info args {gid_groups_conds::begin_problemtype}]] eq 4} {
        gid_groups_conds::begin_problemtype $spdfile [Kratos::GiveKratosDefaultsFile] ""
    } {
        gid_groups_conds::begin_problemtype $spdfile [Kratos::GiveKratosDefaultsFile] "" 0
    }
    if {[gid_themes::GetCurrentTheme] eq "GiD_black"} {
        set gid_groups_conds::imagesdirList [lsearch -all -inline -not -exact $gid_groups_conds::imagesdirList [list [file join [file dirname $spdfile] images]]]
        gid_groups_conds::add_images_dir [file join [file dirname $spdfile] images Black]
        gid_groups_conds::add_images_dir [file join [file dirname $spdfile] images]
    }
}

proc Kratos::GiveKratosDefaultsFile {} {
    variable kratos_private
    set dir_name [file dirname [GiveGidDefaultsFile]]
    set file_name $kratos_private(Name)$kratos_private(Version).ini
    if { $::tcl_platform(platform) == "windows" } {
        return [file join $dir_name $file_name]
    } else {
        return [file join $dir_name .$file_name]
    }
}

# PREFERENCES
proc Kratos::GetPreferencesFilePath { } {
    variable kratos_private
    # Where we store the user preferences :)
    
    # Get the GiD preferences dir
    set dir_name [file dirname [GiveGidDefaultsFile]]

    # Our file is KratosVars.txt
    set file_name $kratos_private(Name)Vars.txt

    # Linux one will start with a point... pijadas
    if { $::tcl_platform(platform) == "windows" } {
        return [file join $dir_name $file_name]
    } else {
        return [file join $dir_name .$file_name]
    }
}

proc Kratos::RegisterEnvironment { } {
    variable kratos_private
    set vars_to_save [list DevMode echo_level mdpa_format]
    set preferences [dict create]
    foreach v $vars_to_save {
        if {[info exists kratos_private($v)]} {
            dict set preferences $v $kratos_private($v)
        }
    }
    
    if {[llength [dict keys $preferences]] > 0} {
        set fp [open [Kratos::GetPreferencesFilePath] w]
        if {[catch {set data [puts $fp [write::tcl2json $preferences]]} ]} {W "Problems saving user prefecences"; W $data}
        close $fp
    }
}

proc Kratos::LoadEnvironment { } {
    variable kratos_private

    # Init variables
    set data ""
    
    catch {
        # Try to open the preferences file
        set fp [open [Kratos::GetPreferencesFilePath] r]
        # Read the preferences
        set data [read $fp]
        # Close the file
        close $fp
    }
    # Preferences are written in json format
    foreach {k v} [write::json2dict $data] {
        # Foreach pair key value, restore it
        set kratos_private($k) $v
    }
}

# LOGS

proc Kratos::LogInitialData { } {
    set initial_data [dict create]
    dict set initial_data GiD_Version [GiD_Info gidversion]
    dict set initial_data Problemtype_Git_Hash "68418871cff2b897f7fb9176827871b339fe5f91"
    
    Kratos::Log [write::tcl2json $initial_data]
}