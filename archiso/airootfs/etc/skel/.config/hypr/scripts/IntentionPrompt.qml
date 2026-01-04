import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: window
    visible: true
    width: 1920
    height: 1080
    title: "Intention Prompt"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint

    // Background Image
    Image {
        anchors.fill: parent
        source: "file://~/.config/hypr/themes/wallpaper_blue.svg"
        fillMode: Image.PreserveAspectCrop
        
        // Dark Overlay matching hyprlock
        Rectangle {
            anchors.fill: parent
            color: "#000000"
            opacity: 0.6
        }
    }

    ColumnLayout {
        anchors.centerIn: parent
        width: 600
        spacing: 30

        Text {
            text: "SESSION COMPLETE"
            color: "#64ff64" // Green accent
            font.pixelSize: 60
            font.family: "JetBrains Mono Nerd Font"
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        Text {
            text: "Define your focus for the next session:"
            color: "white"
            font.pixelSize: 24
            font.family: "JetBrains Mono Nerd Font"
            opacity: 0.8
            Layout.alignment: Qt.AlignHCenter
        }

        TextField {
            id: intentionInput
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            placeholderText: "Type intention..."
            color: "white"
            font.pixelSize: 24
            font.family: "JetBrains Mono Nerd Font"
            horizontalAlignment: TextInput.AlignHCenter
            
            background: Rectangle {
                color: "white"
                opacity: intentionInput.activeFocus ? 0.15 : 0.05
                radius: 10
                border.color: "white"
                border.width: intentionInput.activeFocus ? 2 : 1
            }

            onAccepted: {
                // Print to stdout so Python can read it
                console.log("INTENTION:" + text);
                Qt.quit();
            }
            
            Component.onCompleted: forceActiveFocus()
        }
        
        Button {
            text: "BEGIN FOCUS"
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 200
            Layout.preferredHeight: 50
            
            contentItem: Text {
                text: parent.text
                font.family: "JetBrains Mono Nerd Font"
                font.bold: true
                color: parent.down ? "#aaaaaa" : "white"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            
            background: Rectangle {
                color: "transparent"
                border.color: "white"
                border.width: 2
                radius: 8
                opacity: parent.down ? 0.5 : 1
            }
            
            onClicked: {
                console.log("INTENTION:" + intentionInput.text);
                Qt.quit();
            }
        }
    }
}
