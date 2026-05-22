import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: root
    width: 540
    height: 660
    visible: true
    color: "transparent"
    flags: Qt.Window | Qt.FramelessWindowHint
    title: "Clipboard Manager"

    property var theme: controller.theme
    property string mono: "JetBrainsMono Nerd Font"

    Component.onCompleted: {
        if (initialX >= 0 && initialY >= 0) {
            root.x = initialX
            root.y = initialY
        }
        searchField.forceActiveFocus()
        fadeIn.start()
    }

    Connections {
        target: controller
        function onCloseRequested() { Qt.quit() }
    }

    NumberAnimation {
        id: fadeIn
        target: container
        property: "opacity"
        from: 0.0
        to: 1.0
        duration: 160
        easing.type: Easing.OutCubic
    }

    Rectangle {
        id: container
        anchors.fill: parent
        radius: 16
        color: root.theme.bg
        border.color: root.theme.accent
        border.width: 1
        opacity: 0.0

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: 15
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.03) }
                GradientStop { position: 1.0; color: Qt.rgba(0, 0, 0, 0.15) }
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 10

            // ----- Header: search + close -----
            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    radius: 10
                    color: Qt.rgba(1, 1, 1, 0.05)
                    border.color: searchField.activeFocus ? root.theme.accent : Qt.rgba(1, 1, 1, 0.08)
                    border.width: 1
                    Behavior on border.color { ColorAnimation { duration: 120 } }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 10
                        spacing: 10

                        Text {
                            text: ""
                            color: root.theme.fg
                            opacity: searchField.activeFocus ? 1.0 : 0.55
                            font.family: root.mono
                            font.pixelSize: 13
                            Behavior on opacity { NumberAnimation { duration: 120 } }
                        }
                        TextField {
                            id: searchField
                            Layout.fillWidth: true
                            placeholderText: "search clipboard…"
                            color: "white"
                            placeholderTextColor: Qt.rgba(1, 1, 1, 0.3)
                            background: Item {}
                            font.family: root.mono
                            font.pixelSize: 13
                            selectByMouse: true
                            onTextChanged: controller.setFilter(text)
                            Keys.onEscapePressed: {
                                if (text.length > 0) text = ""
                                else Qt.quit()
                            }
                            Keys.onDownPressed: historyList.focusFirst()
                            Keys.onReturnPressed: {
                                if (historyList.count > 0) {
                                    var id = historyList.model.data(
                                        historyList.model.index(0, 0), 257)
                                    controller.paste(id, false)
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 40
                    Layout.preferredHeight: 40
                    radius: 10
                    color: closeMouse.containsMouse ? Qt.rgba(1, 0.35, 0.35, 0.18) : Qt.rgba(1, 1, 1, 0.05)
                    border.color: closeMouse.containsMouse ? Qt.rgba(1, 0.5, 0.5, 0.5) : Qt.rgba(1, 1, 1, 0.08)
                    border.width: 1
                    Behavior on color { ColorAnimation { duration: 100 } }

                    Text {
                        anchors.centerIn: parent
                        text: ""
                        color: "white"
                        opacity: 0.8
                        font.family: root.mono
                        font.pixelSize: 13
                    }
                    MouseArea {
                        id: closeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: Qt.quit()
                    }
                }
            }

            // ----- Pinned section -----
            ColumnLayout {
                Layout.fillWidth: true
                visible: pinsList.count > 0
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    Text {
                        text: "  PINNED"
                        color: root.theme.fg
                        font.family: root.mono
                        font.pixelSize: 10
                        font.letterSpacing: 1.5
                        font.bold: true
                        opacity: 0.7
                    }
                    Text {
                        text: pinsList.count
                        color: "white"
                        opacity: 0.35
                        font.family: root.mono
                        font.pixelSize: 10
                    }
                    Item { Layout.fillWidth: true }
                }

                ListView {
                    id: pinsList
                    Layout.fillWidth: true
                    Layout.preferredHeight: 96
                    orientation: ListView.Horizontal
                    spacing: 8
                    clip: true
                    model: controller.pinsModel
                    delegate: pinCardDelegate
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.horizontal: ScrollBar {
                        policy: ScrollBar.AsNeeded
                        opacity: 0.5
                    }
                }
            }

            // ----- History header -----
            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Text {
                    text: "  HISTORY"
                    color: root.theme.fg
                    font.family: root.mono
                    font.pixelSize: 10
                    font.letterSpacing: 1.5
                    font.bold: true
                    opacity: 0.7
                }
                Text {
                    text: historyList.count
                    color: "white"
                    opacity: 0.35
                    font.family: root.mono
                    font.pixelSize: 10
                }
                Item { Layout.fillWidth: true }
                Rectangle {
                    Layout.preferredWidth: 90
                    Layout.preferredHeight: 24
                    radius: 6
                    color: wipeMouse.containsMouse ? Qt.rgba(1, 0.3, 0.3, 0.18) : "transparent"
                    border.color: wipeMouse.containsMouse ? Qt.rgba(1, 0.45, 0.45, 0.45) : Qt.rgba(1, 1, 1, 0.1)
                    border.width: 1
                    Behavior on color { ColorAnimation { duration: 100 } }
                    Text {
                        anchors.centerIn: parent
                        text: "  wipe all"
                        color: "white"
                        opacity: wipeMouse.containsMouse ? 0.95 : 0.55
                        font.family: root.mono
                        font.pixelSize: 10
                    }
                    MouseArea {
                        id: wipeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: wipeConfirm.visible = true
                    }
                }
            }

            // ----- History list -----
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 10
                color: Qt.rgba(0, 0, 0, 0.22)
                border.color: Qt.rgba(1, 1, 1, 0.05)
                border.width: 1

                ListView {
                    id: historyList
                    anchors.fill: parent
                    anchors.margins: 4
                    clip: true
                    spacing: 2
                    model: controller.historyModel
                    delegate: rowDelegate
                    boundsBehavior: Flickable.StopAtBounds
                    highlightFollowsCurrentItem: true
                    keyNavigationEnabled: true
                    ScrollBar.vertical: ScrollBar { opacity: 0.5 }

                    function focusFirst() {
                        if (count > 0) {
                            currentIndex = 0
                            forceActiveFocus()
                        }
                    }

                    function actOnCurrent(action) {
                        if (currentIndex < 0 || currentIndex >= count) return
                        var id = model.data(model.index(currentIndex, 0), 257)
                        action(id)
                    }

                    Keys.onEscapePressed: Qt.quit()
                    Keys.onPressed: (e) => {
                        if (e.key === Qt.Key_Return || e.key === Qt.Key_Enter) {
                            actOnCurrent(function(id) { controller.paste(id, false) })
                            e.accepted = true
                        } else if (e.key === Qt.Key_Delete) {
                            actOnCurrent(function(id) { controller.deleteItem(id, false) })
                            e.accepted = true
                        } else if ((e.modifiers & Qt.ControlModifier) && e.key === Qt.Key_P) {
                            actOnCurrent(function(id) { controller.togglePin(id, false) })
                            e.accepted = true
                        } else if (e.key === Qt.Key_Slash) {
                            searchField.forceActiveFocus()
                            searchField.selectAll()
                            e.accepted = true
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: historyList.count === 0
                    text: searchField.text.length > 0
                        ? "No matches"
                        : "Clipboard is empty"
                    color: "white"
                    opacity: 0.3
                    font.family: root.mono
                    font.pixelSize: 13
                }
            }
        }
    }

    // ===== Row delegate =====
    Component {
        id: rowDelegate

        Item {
            id: rowItem
            width: ListView.view.width
            height: kind === "image" ? 84 : 58

            required property string itemId
            required property string kind
            required property string preview
            required property string detail
            required property string imageSrc
            required property bool isPinned
            required property int index

            property bool selected: ListView.isCurrentItem
            property bool hovered: rowMouse.containsMouse

            Rectangle {
                anchors.fill: parent
                radius: 8
                color: rowItem.selected
                    ? Qt.rgba(1, 1, 1, 0.09)
                    : (rowItem.hovered ? Qt.rgba(1, 1, 1, 0.04) : "transparent")
                border.color: rowItem.selected ? root.theme.accent : "transparent"
                border.width: 1
                Behavior on color { ColorAnimation { duration: 80 } }

                Rectangle {
                    width: 3
                    height: parent.height * 0.55
                    anchors.left: parent.left
                    anchors.leftMargin: 1
                    anchors.verticalCenter: parent.verticalCenter
                    color: root.theme.accent
                    radius: 2
                    opacity: rowItem.selected ? 1.0 : 0.0
                    Behavior on opacity { NumberAnimation { duration: 100 } }
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 8
                    spacing: 12

                    // Thumbnail / type icon slot
                    Item {
                        Layout.preferredWidth: rowItem.kind === "image" ? 68 : 26
                        Layout.preferredHeight: rowItem.kind === "image" ? 68 : 26
                        Layout.alignment: Qt.AlignVCenter

                        Rectangle {
                            visible: rowItem.kind === "image"
                            anchors.fill: parent
                            radius: 6
                            color: Qt.rgba(0, 0, 0, 0.3)
                            border.color: Qt.rgba(1, 1, 1, 0.08)
                            border.width: 1
                            clip: true
                            Image {
                                anchors.fill: parent
                                anchors.margins: 2
                                source: rowItem.imageSrc
                                asynchronous: true
                                cache: true
                                fillMode: Image.PreserveAspectCrop
                                sourceSize.width: 128
                                sourceSize.height: 128
                            }
                        }
                        Text {
                            visible: rowItem.kind === "text"
                            anchors.centerIn: parent
                            text: ""
                            color: root.theme.fg
                            opacity: 0.55
                            font.family: root.mono
                            font.pixelSize: 14
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 3
                        Text {
                            visible: rowItem.kind === "text"
                            text: rowItem.preview
                            color: "white"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            font.family: root.mono
                            font.pixelSize: 13
                        }
                        Text {
                            text: rowItem.detail
                            color: "white"
                            opacity: 0.4
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            font.family: root.mono
                            font.pixelSize: 10
                        }
                    }

                    Row {
                        spacing: 4
                        Layout.alignment: Qt.AlignVCenter
                        opacity: rowItem.hovered || rowItem.selected ? 1.0 : 0.0
                        Behavior on opacity { NumberAnimation { duration: 120 } }

                        Rectangle {
                            width: 30; height: 30; radius: 6
                            color: pinMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.14) : "transparent"
                            border.color: pinMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.15) : "transparent"
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: ""
                                color: "white"
                                opacity: 0.7
                                font.family: root.mono
                                font.pixelSize: 12
                            }
                            MouseArea {
                                id: pinMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: controller.togglePin(rowItem.itemId, rowItem.isPinned)
                            }
                        }
                        Rectangle {
                            width: 30; height: 30; radius: 6
                            color: delMouse.containsMouse ? Qt.rgba(1, 0.3, 0.3, 0.22) : "transparent"
                            border.color: delMouse.containsMouse ? Qt.rgba(1, 0.45, 0.45, 0.4) : "transparent"
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: ""
                                color: "white"
                                opacity: 0.7
                                font.family: root.mono
                                font.pixelSize: 12
                            }
                            MouseArea {
                                id: delMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: controller.deleteItem(rowItem.itemId, rowItem.isPinned)
                            }
                        }
                    }
                }

                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton
                    z: -1
                    cursorShape: Qt.PointingHandCursor
                    onClicked: controller.paste(rowItem.itemId, rowItem.isPinned)
                    onPositionChanged: rowItem.ListView.view.currentIndex = rowItem.index
                }
            }
        }
    }

    // ===== Pin card delegate =====
    Component {
        id: pinCardDelegate

        Rectangle {
            id: card
            required property string itemId
            required property string kind
            required property string preview
            required property string detail
            required property string imageSrc
            required property bool isPinned

            width: kind === "image" ? 92 : 150
            height: 88
            radius: 10
            color: cardMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.1) : Qt.rgba(1, 1, 1, 0.05)
            border.color: cardMouse.containsMouse ? root.theme.accent : Qt.rgba(1, 1, 1, 0.1)
            border.width: 1
            Behavior on color { ColorAnimation { duration: 100 } }
            Behavior on border.color { ColorAnimation { duration: 100 } }

            Text {
                id: pinGlyph
                text: ""
                color: root.theme.accent
                font.family: root.mono
                font.pixelSize: 9
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.margins: 6
            }

            Rectangle {
                width: 20; height: 20; radius: 5
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 4
                visible: cardMouse.containsMouse || unpinMouse.containsMouse
                color: unpinMouse.containsMouse ? Qt.rgba(1, 0.3, 0.3, 0.28) : Qt.rgba(0, 0, 0, 0.4)
                border.color: unpinMouse.containsMouse ? Qt.rgba(1, 0.5, 0.5, 0.6) : Qt.rgba(1, 1, 1, 0.15)
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: ""
                    color: "white"
                    opacity: 0.85
                    font.family: root.mono
                    font.pixelSize: 9
                }
                MouseArea {
                    id: unpinMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: controller.togglePin(card.itemId, true)
                }
            }

            Image {
                visible: card.kind === "image"
                anchors.top: pinGlyph.bottom
                anchors.topMargin: 4
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 6
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width - 16
                source: card.imageSrc
                asynchronous: true
                cache: true
                fillMode: Image.PreserveAspectFit
                sourceSize.width: 128
                sourceSize.height: 128
            }
            Text {
                visible: card.kind === "text"
                anchors.top: pinGlyph.bottom
                anchors.topMargin: 4
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                anchors.bottomMargin: 6
                text: card.preview
                color: "white"
                wrapMode: Text.Wrap
                elide: Text.ElideRight
                maximumLineCount: 4
                font.family: root.mono
                font.pixelSize: 10
                lineHeight: 1.1
            }

            MouseArea {
                id: cardMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                z: -1
                onClicked: controller.paste(card.itemId, true)
            }
        }
    }

    // ===== Wipe confirm overlay =====
    Rectangle {
        id: wipeConfirm
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.65)
        visible: false
        radius: 16
        z: 100

        MouseArea {
            anchors.fill: parent
            onClicked: wipeConfirm.visible = false
        }

        Rectangle {
            anchors.centerIn: parent
            width: 340
            height: 160
            radius: 12
            color: root.theme.bg
            border.color: root.theme.accent
            border.width: 1

            MouseArea { anchors.fill: parent }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 10

                Text {
                    text: "Clear all clipboard history?"
                    color: "white"
                    font.family: root.mono
                    font.pixelSize: 13
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "Pinned items will be kept."
                    color: "white"
                    opacity: 0.5
                    font.family: root.mono
                    font.pixelSize: 10
                    Layout.alignment: Qt.AlignHCenter
                }
                Item { Layout.fillHeight: true }
                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 12

                    Rectangle {
                        width: 96; height: 34; radius: 6
                        color: cancelMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : Qt.rgba(1, 1, 1, 0.05)
                        border.color: Qt.rgba(1, 1, 1, 0.1); border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "Cancel"; color: "white"
                            font.family: root.mono; font.pixelSize: 11
                        }
                        MouseArea {
                            id: cancelMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: wipeConfirm.visible = false
                        }
                    }
                    Rectangle {
                        width: 96; height: 34; radius: 6
                        color: confirmMouse.containsMouse ? Qt.rgba(1, 0.3, 0.3, 0.32) : Qt.rgba(1, 0.3, 0.3, 0.15)
                        border.color: Qt.rgba(1, 0.45, 0.45, 0.55); border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "Wipe"; color: "white"
                            font.family: root.mono; font.pixelSize: 11; font.bold: true
                        }
                        MouseArea {
                            id: confirmMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: { controller.wipe(); wipeConfirm.visible = false }
                        }
                    }
                }
            }
        }
    }
}
