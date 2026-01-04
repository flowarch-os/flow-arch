import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.LocalStorage 2.0
import "quotes.js" as Quotes

Rectangle {
    id: container
    width: 1920
    height: 1080
    color: "#0a0a0a"

    property int sessionIndex: sessionModel.lastIndex
    property var db: null
    property string displayName: userModel.lastUser || "Rockstar"
    property string motivation: ""
    property bool isStrict: false
    property bool isSleep: false
    property bool showSchedule: false
    
    function getRandomQuote() {
        var index = Math.floor(Math.random() * Quotes.list.length);
        return Quotes.list[index].arg(displayName);
    }

    function checkSleep(json) {
        var startStr = json.bedtime_start || "23:00";
        var endStr = json.bedtime_end || "05:00";
        
        var sh = parseInt(startStr.split(":")[0]);
        var eh = parseInt(endStr.split(":")[0]);
        
        var now = new Date();
        var h = now.getHours();
        
        var sleeping = false;
        if (sh > eh) { // Crosses midnight (e.g. 23 to 5)
            if (h >= sh || h < eh) sleeping = true;
        } else { // Same day (e.g. 1 to 5)
            if (h >= sh && h < eh) sleeping = true;
        }
        
        return sleeping;
    }

    function parseLocalISO(s) {
        var b = s.split(/\D+/);
        return new Date(b[0], b[1]-1, b[2], b[3], b[4], b[5]);
    }

    function checkCalendar(json) {
        if (!json.calendar_events) return null;
        var now = new Date();
        for (var i = 0; i < json.calendar_events.length; i++) {
            var event = json.calendar_events[i];
            var start = parseLocalISO(event.start);
            var end = parseLocalISO(event.end);
            if (now >= start && now < end) {
                return event;
            }
        }
        return null;
    }
    
    function loadGoals() {
        var xhr = new XMLHttpRequest();
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                goalModel.clear();
                eventModel.clear();
                taskModel.clear();
                
                var loaded = false;
                if (xhr.status === 200 || xhr.status === 0) {
                    try {
                        var json = JSON.parse(xhr.responseText);
                        
                        // Goals
                        if (json.goals) {
                            for (var i = 0; i < json.goals.length; i++) {
                                goalModel.append({text: json.goals[i]});
                            }
                            loaded = true;
                        }

                        // Strict Mode Check
                        var event = checkCalendar(json);
                        if (event) {
                            goalCombo.editText = event.goal;
                            intentionField.text = event.intention;
                            isStrict = true;
                            
                            var end = new Date(event.end);
                            var diff = (end - new Date()) / 60000;
                            timeSlider.value = Math.max(5, Math.min(240, Math.round(diff/5)*5));
                        }
                        
                        // Sleep Check
                        if (checkSleep(json)) {
                            isSleep = true;
                            sleepTimer.start();
                        }
                        
                        // Populate Events (Today)
                        if (json.calendar_events) {
                            var today = new Date().toDateString();
                            var todaysEvents = [];
                            
                            for (var j = 0; j < json.calendar_events.length; j++) {
                                var e = json.calendar_events[j];
                                var startDt = parseLocalISO(e.start);
                                if (startDt.toDateString() === today) {
                                    e.startTime = startDt;
                                    todaysEvents.push(e);
                                }
                            }
                            // Sort
                            todaysEvents.sort(function(a, b) { return a.startTime - b.startTime });
                            
                            for (var k = 0; k < todaysEvents.length; k++) {
                                var te = todaysEvents[k];
                                var timeStr = Qt.formatTime(te.startTime, "h:mm ap");
                                eventModel.append({
                                    time: timeStr,
                                    goal: te.goal || "",
                                    intention: te.intention || ""
                                });
                            }
                        }
                        
                        // Populate Tasks
                        if (json.tasks) {
                            for (var t = 0; t < json.tasks.length; t++) {
                                var task = json.tasks[t];
                                if (!task.done) {
                                    taskModel.append({title: task.title, goal: task.goal || ""});
                                }
                            }
                        }
                        
                    } catch (e) {
                        console.log("JSON Parse error: " + e);
                    }
                }
                
                if (!loaded) {
                    goalModel.append({text: "Work"});
                    goalModel.append({text: "Study"});
                }
            }
        }
        // xhr.open("GET", "file:///home/malek/.config/hypr/settings.json");
        // For the ISO, we will just use defaults and skip reading the user config
        goalModel.clear();
        goalModel.append({text: "Work"});
        goalModel.append({text: "Study"});
        return;
        xhr.send();
    }

    function saveAndLogin() {
        if (isSleep) return;
        var currentGoal = goalCombo.editText;
        // db.transaction skipped - using settings.json as source of truth
        
        var data = {
            "goal": currentGoal,
            "intention": intentionField.text,
            "duration": timeSlider.value,
            "pomodoro": pomodoroCheck.checked
        };
        var xhr = new XMLHttpRequest();
        xhr.open("PUT", "file:///tmp/sddm_session.json");
        xhr.send(JSON.stringify(data));
        sddm.login(userModel.lastUser, passwordField.text, container.sessionIndex);
    }
    
    ListModel { id: eventModel }
    ListModel { id: taskModel }
    
    // --- SCHEDULE OVERLAY ---
    Rectangle {
        id: schedulePanel
        width: 400
        height: parent.height
        anchors.right: parent.right
        color: "#1a1a1a"
        opacity: showSchedule ? 0.95 : 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 200 } }
        z: 10
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 20
            
            Text { 
                text: "Today's Schedule"
                color: "white"
                font.pixelSize: 24
                font.bold: true
            }
            
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredHeight: 1
                model: eventModel
                clip: true
                spacing: 10
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { active: true }
                delegate: Column {
                    width: parent.width
                    spacing: 2
                    Text { text: time; color: "#888"; font.pixelSize: 12 }
                    Text { text: goal; color: "white"; font.bold: true; font.pixelSize: 14 }
                    Text { text: intention; color: "#ccc"; font.pixelSize: 13; wrapMode: Text.Wrap; width: parent.width }
                    Item { width: parent.width; height: 5 }
                    Rectangle { width: parent.width; height: 1; color: "#333" }
                }
            }
            
            Text { 
                text: "Tasks"
                color: "white"
                font.pixelSize: 24
                font.bold: true
                Layout.topMargin: 20
            }
            
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredHeight: 1
                model: taskModel
                clip: true
                spacing: 8
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { active: true }
                delegate: RowLayout {
                    width: parent.width
                    spacing: 10
                    Rectangle { width: 14; height: 14; radius: 4; border.color: "#666"; color: "transparent" }
                    Column {
                        Layout.fillWidth: true
                        Text { text: title; color: "white"; font.pixelSize: 14; wrapMode: Text.Wrap; width: parent.width }
                        Text { text: goal; color: "#666"; font.pixelSize: 10; visible: goal !== "" }
                    }
                }
            }
        }
    }
    
    // --- SHOW SCHEDULE BUTTON ---
    Button {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 20
        text: showSchedule ? "Hide Schedule" : "Show Schedule"
        z: 20
        
        background: Rectangle {
            color: "transparent"
            border.color: "white"
            border.width: 1
            radius: 4
            opacity: 0.5
        }
        contentItem: Text {
            text: parent.text
            color: "white"
            font.pixelSize: 12
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            leftPadding: 10; rightPadding: 10; topPadding: 5; bottomPadding: 5
        }
        onClicked: showSchedule = !showSchedule
    }

    Timer {
        id: sleepTimer
        interval: 4000
        repeat: false
        onTriggered: sddm.powerOff()
    }
    
    Rectangle {
        id: sleepOverlay
        anchors.fill: parent
        color: "black"
        z: 999
        visible: isSleep
        
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 20
            
            Text {
                text: "It's your bedtime :)"
                color: "white"
                font.pixelSize: 48
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            
            Text {
                text: "Shutting down..."
                color: "#ff5555"
                font.pixelSize: 24
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    ListModel { id: goalModel }

    Component.onCompleted: {
        loadGoals();
        motivation = getRandomQuote();
        passwordField.forceActiveFocus();
    }

    ColumnLayout {
        anchors.centerIn: parent
        width: 400
        spacing: 15

        // Time and Motivation
        ColumnLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 0
            Text {
                text: Qt.formatDateTime(new Date(), "h:mm ap")
                color: "white"
                font.pixelSize: 96
                font.weight: Font.ExtraLight
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: motivation
                color: "white"
                opacity: 0.6
                font.pixelSize: 16
                font.italic: true
                Layout.alignment: Qt.AlignHCenter
                Layout.bottomMargin: 30
            }
        }

        // --- PASSWORD ---
        TextField {
            id: passwordField
            placeholderText: "Password"
            echoMode: TextInput.Password
            Layout.fillWidth: true
            font.pixelSize: 16
            color: "white"
            selectByMouse: true
            background: Rectangle { 
                color: "white"
                opacity: passwordField.activeFocus ? 0.12 : 0.05
                radius: 8
                border.color: "white"
                border.width: passwordField.activeFocus ? 1 : 0
            }
            onAccepted: goalCombo.focus = true
            KeyNavigation.tab: goalCombo
        }

        // --- GOAL PICKER ---
        RowLayout {
            Layout.fillWidth: true
            Text { text: "SESSION GOAL"; color: "white"; opacity: 0.4; font.pixelSize: 10; font.bold: true }
            Item { Layout.fillWidth: true }
            Text { 
                text: "STRICT MODE ACTIVE"
                color: "#ff5555"
                font.pixelSize: 10
                font.bold: true
                visible: isStrict
            }
        }
        ComboBox {
            id: goalCombo
            model: goalModel
            textRole: "text"
            editable: !isStrict
            enabled: !isStrict
            Layout.fillWidth: true
            font.pixelSize: 15
            opacity: isStrict ? 0.5 : 1.0
            
            background: Rectangle { 
                color: "white"
                opacity: goalCombo.activeFocus ? 0.12 : 0.05
                radius: 8
                border.color: "white"
                border.width: goalCombo.activeFocus ? 1 : 0
            }
            
            contentItem: TextField {
                text: goalCombo.editText
                color: "white"
                leftPadding: 12
                verticalAlignment: TextInput.AlignVCenter
                background: null
                enabled: !isStrict
                onAccepted: intentionField.forceActiveFocus()
            }

            Keys.onPressed: (event) => {
                if (event.key === Qt.Key_Delete && (event.modifiers & Qt.ShiftModifier)) {
                    var txt = goalCombo.currentText;
                    db.transaction(function(tx) { tx.executeSql('DELETE FROM goals WHERE goal=?', [txt]); });
                    for(var i=0; i<goalModel.count; i++) if(goalModel.get(i).text === txt) goalModel.remove(i);
                    event.accepted = true;
                }
            }
            KeyNavigation.tab: intentionField
            KeyNavigation.backtab: passwordField
        }

        // --- INTENTION ---
        Text { text: "INTENTION"; color: "white"; opacity: 0.4; font.pixelSize: 10; font.bold: true; Layout.leftMargin: 5 }
        TextField {
            id: intentionField
            placeholderText: "What's the mission?"
            Layout.fillWidth: true
            font.pixelSize: 15
            color: "white"
            enabled: !isStrict
            opacity: isStrict ? 0.5 : 1.0
            background: Rectangle { 
                color: "white"
                opacity: intentionField.activeFocus ? 0.12 : 0.05
                radius: 8
                border.color: "white"
                border.width: intentionField.activeFocus ? 1 : 0
            }
            onAccepted: saveAndLogin()
            KeyNavigation.tab: pomodoroCheck
            KeyNavigation.backtab: goalCombo
        }

        // --- POMODORO CHECKBOX ---
        CheckBox {
            id: pomodoroCheck
            text: "POMODORO MODE (25m / 5m)"
            Layout.fillWidth: true
            enabled: !isStrict
            opacity: isStrict ? 0.5 : 1.0
            
            contentItem: Text {
                text: pomodoroCheck.text
                font.pixelSize: 14
                font.bold: true
                color: "white"
                verticalAlignment: Text.AlignVCenter
                leftPadding: pomodoroCheck.indicator.width + pomodoroCheck.spacing
            }
            
            indicator: Rectangle {
                implicitWidth: 20
                implicitHeight: 20
                x: pomodoroCheck.leftPadding
                y: parent.height / 2 - height / 2
                radius: 4
                color: "transparent"
                border.color: "white"
                border.width: 1
                
                Rectangle {
                    width: 12
                    height: 12
                    x: 4
                    y: 4
                    radius: 2
                    color: "white"
                    visible: pomodoroCheck.checked
                }
            }
            KeyNavigation.tab: timeSlider
            KeyNavigation.backtab: intentionField
        }

        // --- TIME SLIDER ---
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 12
            Layout.topMargin: 5
            visible: !pomodoroCheck.checked
            opacity: isStrict ? 0.5 : 1.0
            
            RowLayout {
                Layout.fillWidth: true
                Text { text: "TIME LIMIT"; color: "white"; opacity: 0.4; font.pixelSize: 10; font.bold: true }
                Item { Layout.fillWidth: true }
                Text { text: timeSlider.value + " min"; color: "white"; font.bold: true; font.pixelSize: 14 }
            }

            Slider {
                id: timeSlider
                from: 5
                to: 240
                stepSize: 5
                value: 60
                Layout.fillWidth: true
                focus: true
                enabled: !isStrict
                
                handle: Rectangle {
                    x: timeSlider.leftPadding + timeSlider.visualPosition * (timeSlider.availableWidth - width)
                    y: timeSlider.topPadding + timeSlider.availableHeight / 2 - height / 2
                    width: 16; height: 16; radius: 8
                    color: timeSlider.activeFocus ? "white" : "#666"
                    border.color: "white"
                    border.width: 2
                }
                
                background: Rectangle {
                    x: timeSlider.leftPadding
                    y: timeSlider.topPadding + timeSlider.availableHeight / 2 - height / 2
                    width: timeSlider.availableWidth; height: 4; radius: 2; color: "white"; opacity: 0.1
                    Rectangle {
                        width: timeSlider.visualPosition * parent.width; height: parent.height; color: "white"; radius: 2; opacity: 0.6
                    }
                }
                
                Keys.onLeftPressed: value -= stepSize
                Keys.onRightPressed: value += stepSize
                KeyNavigation.tab: loginButton
                KeyNavigation.backtab: intentionField
            }
        }

        // --- LOGIN BUTTON ---
        Button {
            id: loginButton
            text: "LAUNCH"
            Layout.fillWidth: true
            Layout.preferredHeight: 50
            Layout.topMargin: 20
            
            contentItem: Text { 
                text: parent.text
                color: loginButton.activeFocus ? "black" : "white"
                font.bold: true
                font.letterSpacing: 2
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter 
            }
            
            background: Rectangle { 
                color: loginButton.activeFocus ? "white" : "transparent"
                radius: 8
                border.color: "white"
                border.width: 1
            }
            
            onClicked: saveAndLogin()
            Keys.onReturnPressed: saveAndLogin()
            Keys.onEnterPressed: saveAndLogin()
            KeyNavigation.backtab: timeSlider
        }

        Text {
            text: sddm.loginErrorMessage || ""
            color: "#ff5555"
            font.pixelSize: 12
            visible: text !== ""
            Layout.alignment: Qt.AlignHCenter
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: passwordField.forceActiveFocus()
        z: -1
    }
}
