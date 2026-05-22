import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

ApplicationWindow {
    id: root
    visible: true
    width: 920
    height: 620
    title: "App Picker"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog
    color: "transparent"

    // Theme props (loaded from /tmp/app_picker_data.json at startup)
    property string bgColor: "#0a1a2e"
    property string fgColor: "#5fbaff"
    property string accent: "#5fbaff"
    property string dimAccent: "#1a3a5e"
    property string dataJsonPath: "/tmp/app_picker_data.json"

    // State
    property var allApps: []
    property var filteredApps: []
    property string query: ""

    // ----- helpers -----
    function hexToRgba(hex, a) {
        var h = hex.replace("#", "");
        if (h.length === 3)
            h = h[0]+h[0]+h[1]+h[1]+h[2]+h[2];
        var r = parseInt(h.substring(0,2), 16) / 255.0;
        var g = parseInt(h.substring(2,4), 16) / 255.0;
        var b = parseInt(h.substring(4,6), 16) / 255.0;
        return Qt.rgba(r, g, b, a);
    }

    function loadApps() {
        var xhr = new XMLHttpRequest();
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                try {
                    var data = JSON.parse(xhr.responseText);
                    if (data.theme) {
                        if (data.theme.bgColor)   bgColor   = data.theme.bgColor;
                        if (data.theme.fgColor)   fgColor   = data.theme.fgColor;
                        if (data.theme.accent)    accent    = data.theme.accent;
                        if (data.theme.dimAccent) dimAccent = data.theme.dimAccent;
                    }
                    allApps = data.apps || [];
                } catch (e) {
                    allApps = [];
                }
                refilter();
            }
        };
        xhr.open("GET", "file://" + dataJsonPath);
        xhr.send();
    }

    function refilter() {
        var q = query.trim().toLowerCase();
        if (q === "") {
            filteredApps = allApps;
        } else {
            var out = [];
            for (var i = 0; i < allApps.length; i++) {
                var a = allApps[i];
                var n = (a.name || "").toLowerCase();
                var c = (a.comment || "").toLowerCase();
                var e = (a.exec || "").toLowerCase();
                if (n.indexOf(q) >= 0 || c.indexOf(q) >= 0 || e.indexOf(q) >= 0) {
                    out.push(a);
                }
            }
            filteredApps = out;
        }
        grid.currentIndex = filteredApps.length > 0 ? 0 : -1;
    }

    function launchSelected() {
        if (grid.currentIndex < 0 || grid.currentIndex >= filteredApps.length)
            return;
        var app = filteredApps[grid.currentIndex];
        console.log("LAUNCH:" + app.exec);
        Qt.quit();
    }

    Component.onCompleted: loadApps()

    // ----- chrome -----
    Rectangle {
        id: chrome
        anchors.fill: parent
        anchors.margins: 1
        color: root.hexToRgba(root.bgColor, 0.93)
        radius: 16
        border.color: root.accent
        border.width: 2

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 18

            // ----- search bar -----
            Rectangle {
                Layout.fillWidth: true
                height: 52
                color: "transparent"

                RowLayout {
                    anchors.fill: parent
                    spacing: 14

                    Text {
                        text: ""   // FA search glyph
                        font.family: "JetBrainsMono Nerd Font"
                        font.pixelSize: 22
                        color: root.dimAccent
                    }

                    TextField {
                        id: searchField
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        placeholderText: "Search applications"
                        color: root.fgColor
                        placeholderTextColor: root.dimAccent
                        font.family: "JetBrainsMono Nerd Font"
                        font.pixelSize: 20
                        verticalAlignment: TextInput.AlignVCenter
                        selectionColor: root.hexToRgba(root.accent, 0.45)
                        selectedTextColor: "white"
                        background: Rectangle {
                            color: "transparent"
                            Rectangle {
                                anchors.bottom: parent.bottom
                                anchors.left: parent.left
                                anchors.right: parent.right
                                height: searchField.activeFocus ? 2 : 1
                                color: searchField.activeFocus ? root.accent : root.dimAccent
                                Behavior on color { ColorAnimation { duration: 120 } }
                            }
                        }
                        onTextChanged: { root.query = text; root.refilter(); }
                        Keys.onPressed: function(event) {
                            if (event.key === Qt.Key_Escape) {
                                if (text.length > 0) { text = ""; }
                                else { Qt.quit(); }
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                root.launchSelected();
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Down) {
                                grid.moveCurrentIndexDown();
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Up) {
                                grid.moveCurrentIndexUp();
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Right && cursorPosition === text.length) {
                                grid.moveCurrentIndexRight();
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Left && cursorPosition === 0) {
                                grid.moveCurrentIndexLeft();
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Tab) {
                                grid.moveCurrentIndexRight();
                                event.accepted = true;
                            }
                        }
                        Component.onCompleted: forceActiveFocus()
                    }

                    Text {
                        text: root.filteredApps.length + " / " + root.allApps.length
                        color: root.dimAccent
                        font.family: "JetBrainsMono Nerd Font"
                        font.pixelSize: 13
                    }
                }
            }

            // ----- divider -----
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: root.hexToRgba(root.accent, 0.18)
            }

            // ----- grid -----
            GridView {
                id: grid
                Layout.fillWidth: true
                Layout.fillHeight: true
                cellWidth: 142
                cellHeight: 132
                clip: true
                model: root.filteredApps.length
                currentIndex: 0
                highlightMoveDuration: 120
                highlightFollowsCurrentItem: true
                cacheBuffer: 600
                boundsBehavior: Flickable.StopAtBounds

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                    contentItem: Rectangle {
                        implicitWidth: 4
                        radius: 2
                        color: root.hexToRgba(root.accent, 0.55)
                    }
                }

                delegate: Item {
                    width: grid.cellWidth
                    height: grid.cellHeight

                    property bool isSelected: GridView.isCurrentItem
                    property var app: root.filteredApps[index]

                    Rectangle {
                        id: bg
                        anchors.fill: parent
                        anchors.margins: 6
                        radius: 10
                        property bool hovered: hover.containsMouse
                        color: (isSelected || hovered)
                               ? root.hexToRgba(root.accent, isSelected ? 0.20 : 0.10)
                               : "transparent"
                        border.width: isSelected ? 1 : 0
                        border.color: root.hexToRgba(root.accent, 0.65)
                        Behavior on color { ColorAnimation { duration: 110 } }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            Item {
                                Layout.alignment: Qt.AlignHCenter
                                Layout.preferredWidth: 52
                                Layout.preferredHeight: 52

                                Image {
                                    anchors.fill: parent
                                    source: app && app.icon ? "file://" + app.icon : ""
                                    fillMode: Image.PreserveAspectFit
                                    smooth: true
                                    asynchronous: true
                                    sourceSize.width: 96
                                    sourceSize.height: 96
                                    visible: app && app.icon !== ""
                                }
                                // Fallback glyph when no icon
                                Text {
                                    anchors.centerIn: parent
                                    text: ""
                                    font.family: "JetBrainsMono Nerd Font"
                                    font.pixelSize: 36
                                    color: root.dimAccent
                                    visible: !app || !app.icon
                                }
                            }

                            Text {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 36
                                text: app ? app.name : ""
                                color: isSelected ? root.accent : root.fgColor
                                font.family: "JetBrainsMono Nerd Font"
                                font.pixelSize: 12
                                font.weight: isSelected ? Font.DemiBold : Font.Normal
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignTop
                                wrapMode: Text.Wrap
                                elide: Text.ElideRight
                                maximumLineCount: 2
                            }
                        }

                        MouseArea {
                            id: hover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                grid.currentIndex = index;
                                root.launchSelected();
                            }
                            onEntered: grid.currentIndex = index
                        }
                    }
                }
            }
        }
    }

    // Click outside chrome closes (covers transparent margin if any)
    MouseArea {
        anchors.fill: parent
        z: -1
        onClicked: Qt.quit()
    }
}
