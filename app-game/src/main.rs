use bevy::prelude::*;

fn setup(mut cmds: Commands) {
    cmds.spawn(Camera2d::default());
}

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_systems(Startup, setup)
        .run();
}
