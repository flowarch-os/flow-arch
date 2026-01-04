import QtQuick 2.15
import QtQuick.Controls 2.15

ApplicationWindow {
    visible: true
    width: Screen.width
    height: Screen.height
    title: "Pomodoro Curtain"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    color: "black"

    Image {
        anchors.fill: parent
        source: "file://~/.config/hypr/themes/wallpaper_blue.svg"
        fillMode: Image.PreserveAspectCrop
        opacity: 0.3 // Dimmed wallpaper
    }
    
    Text {
        anchors.centerIn: parent
        text: "LOCKED"
        color: "white"
        opacity: 0.2
        font.pixelSize: 48
        font.family: "JetBrains Mono Nerd Font"
        font.bold: true
    }
}
