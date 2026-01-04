import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    visible: true
    width: 600
    height: 350
    title: "Check-In"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint

    property string mainGoal: "Main Task"
    property int timeLeft: 10

    Timer {
        interval: 1000; running: true; repeat: true
        onTriggered: {
            if (timeLeft > 1) timeLeft--
            else { console.log("CONTINUE"); Qt.quit() }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#191414"
        border.color: "white"
        border.width: 1
        radius: 12

        ColumnLayout {
            anchors.centerIn: parent
            width: parent.width - 80
            spacing: 20

            Text {
                text: "CHECK-IN"
                color: "#64ff64"
                font.pixelSize: 24
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }

            Text {
                text: "Main Goal: " + mainGoal
                color: "white"
                font.pixelSize: 18
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
            }

            TextField {
                id: input
                placeholderText: "Update sub-task or enter to continue..."
                Layout.fillWidth: true
                color: "white"
                background: Rectangle { color: "#333"; radius: 6 }
                onAccepted: { console.log("NEW:" + text); Qt.quit() }
                Component.onCompleted: forceActiveFocus()
            }

            Text {
                text: "Continuing in " + timeLeft + "s..."
                color: "#888"
                font.pixelSize: 14
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
}
