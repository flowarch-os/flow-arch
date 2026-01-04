import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: window
    visible: true
    width: Screen.width
    height: Screen.height
    title: "Pomodoro Lock"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    color: "#0a0a0a"

    // Background (Same as hyprlock)
    Image {
        anchors.fill: parent
        source: "file://~/.config/hypr/themes/wallpaper_blue.svg"
        fillMode: Image.PreserveAspectCrop
        Rectangle { anchors.fill: parent; color: "black"; opacity: 0.6 }
    }

    Item {
        anchors.centerIn: parent
        width: parent.width
        height: parent.height

        // --- CLOCK (Position 250) ---
        Text {
            y: parent.height/2 - 250 - height/2
            anchors.horizontalCenter: parent.horizontalCenter
            text: Qt.formatDateTime(new Date(), "HH:mm")
            color: "white"
            font.pixelSize: 120
            font.family: "JetBrains Mono Nerd Font"
            font.weight: Font.ExtraLight
        }

        // --- TIMER (Position 100) ---
        Text {
            y: parent.height/2 - 100 - height/2
            anchors.horizontalCenter: parent.horizontalCenter
            text: "00:00"
            color: "#ff6464"
            font.pixelSize: 48
            font.family: "JetBrains Mono Nerd Font"
            font.bold: true
        }

        // --- STATUS (Position 50) ---
        Text {
            y: parent.height/2 - 50 - height/2
            anchors.horizontalCenter: parent.horizontalCenter
            text: "BREAK COMPLETE"
            color: "white"
            opacity: 0.6
            font.pixelSize: 18
            font.family: "JetBrains Mono Nerd Font"
        }

        // --- INTENTION FIELD (Position -120, matches hyprlock second box) ---
        TextField {
            id: intentionField
            y: parent.height/2 + 120 - height/2
            anchors.horizontalCenter: parent.horizontalCenter
            width: 300
            height: 50
            placeholderText: "Enter New Intention"
            color: "white"
            font.pixelSize: 16
            font.family: "JetBrains Mono Nerd Font"
            horizontalAlignment: TextInput.AlignHCenter
            
            background: Rectangle {
                color: "white"
                opacity: intentionField.activeFocus ? 0.15 : 0.05
                radius: 4
                border.color: "#64ff64"
                border.width: 2
            }
            
            onAccepted: {
                console.log("INTENTION:" + text)
            }
            
            Component.onCompleted: forceActiveFocus()
        }
        
        // --- ICON ---
        Text {
            anchors.centerIn: parent
            text: "󱎫"
            color: "white"
            opacity: 0.05
            font.pixelSize: 200
        }
    }
}