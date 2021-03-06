namespace eval DEM::examples {

}

proc DEM::examples::Init { } {
    uplevel #0 [list source [file join $::DEM::dir examples SpheresDrop.tcl]]
    uplevel #0 [list source [file join $::DEM::dir examples CirclesDrop.tcl]]
}

proc DEM::examples::UpdateMenus { } {
    if {$::Model::SpatialDimension eq "3D"} {
        GiDMenu::InsertOption "Kratos" [list "---"] 8 PRE "" "" "" insertafter =
        GiDMenu::InsertOption "Kratos" [list "Spheres drop" ] 8 PRE [list ::DEM::examples::SpheresDrop] "" "" insertafter =
        GiDMenu::InsertOption "Kratos" [list "Circles drop" ] 8 PRE [list ::DEM::examples::CirclesDrop] "" "" insertafter =
    }
    GiDMenu::UpdateMenus
}

DEM::examples::Init