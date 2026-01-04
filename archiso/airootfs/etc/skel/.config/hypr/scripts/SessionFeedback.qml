import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: window
    width: 500
    height: 450
    visible: true
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    title: "Session Feedback"

    SystemPalette { id: activePalette; colorGroup: SystemPalette.Active }

    // Use the theme's window color directly for the window background
    background: Rectangle {
        color: activePalette.window
        border.color: activePalette.mid
        border.width: 1
        // radius: 12 // Optional: GTK apps usually aren't rounded unless the theme says so
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 30
        spacing: 20

        Label {
            text: "Session Complete"
            font.pixelSize: 24
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
            color: activePalette.windowText
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: activePalette.mid
        }

                    // Context Info
                ColumnLayout {
                    spacing: 5
                    Label { 
                        text: "GOAL: " + window.mainGoal 
                        font.pixelSize: 14
                        font.bold: true 
                        color: activePalette.windowText
                    }
                    Label { 
                        text: "INTENTION: " + window.mainIntention 
                        font.pixelSize: 14 
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                        opacity: 0.8
                        color: activePalette.windowText
                    }
                }
        // Rating
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 10
            
            RowLayout {
                Layout.fillWidth: true
                Label { text: "Productivity Rating"; font.bold: true; color: activePalette.windowText }
                Item { Layout.fillWidth: true }
                Label { text: Math.round(ratingSlider.value) + "/10"; color: activePalette.highlight; font.bold: true; font.pixelSize: 16 }
            }

            Slider {
                id: ratingSlider
                from: 1
                to: 10
                stepSize: 1
                value: 5
                Layout.fillWidth: true
            }
        }

        // Comment
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 5
            Label { text: "Comments / Retrospective"; font.bold: true; color: activePalette.windowText }
            
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: 80
                
                TextArea {
                    id: commentField
                    placeholderText: "What went well? What didn't?"
                    wrapMode: TextEdit.Wrap
                    focus: true
                    // Ensure text area background is also theme-consistent
                    background: Rectangle {
                        color: activePalette.base
                        border.color: commentField.activeFocus ? activePalette.highlight : activePalette.mid
                        radius: 4
                    }
                }
            }
        }

        // Buttons
        RowLayout {
            Layout.fillWidth: true
            spacing: 20
            Layout.topMargin: 10

            Button {
                text: "Skip"
                Layout.preferredWidth: 100
                flat: true
                onClicked: {
                    console.log("SKIP");
                    Qt.quit();
                }
            }

            Button {
                text: "Submit & Close"
                Layout.fillWidth: true
                highlighted: true
                
                onClicked: {
                    console.log("RATING:" + Math.round(ratingSlider.value));
                    console.log("COMMENT:" + commentField.text.replace(/\n/g, " "));
                    Qt.quit();
                }
            }
        }
    }
}
