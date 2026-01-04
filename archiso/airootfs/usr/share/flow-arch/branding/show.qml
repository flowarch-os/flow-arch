/* === This file is part of Calamares - <https://calamares.io> === */

import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation
{
    id: presentation

    function nextSlide() {
        presentation.goToNextSlide();
    }

    Timer {
        id: advanceTimer
        interval: 5000 // Time per slide in ms
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: nextSlide()
    }

    // Slide 1
    Slide {
        anchors.fill: parent
        Image {
            id: slide1
            source: "slide1.png"
            width: parent.width; height: parent.height
            fillMode: Image.PreserveAspectFit
            anchors.centerIn: parent
        }
    }

    // Slide 2
    Slide {
        anchors.fill: parent
        Image {
            id: slide2
            source: "slide2.png"
            width: parent.width; height: parent.height
            fillMode: Image.PreserveAspectFit
            anchors.centerIn: parent
        }
    }

    // Slide 3
    Slide {
        anchors.fill: parent
        Image {
            id: slide3
            source: "slide3.png"
            width: parent.width; height: parent.height
            fillMode: Image.PreserveAspectFit
            anchors.centerIn: parent
        }
    }

    // Slide 4
    Slide {
        anchors.fill: parent
        Image {
            id: slide4
            source: "slide4.png"
            width: parent.width; height: parent.height
            fillMode: Image.PreserveAspectFit
            anchors.centerIn: parent
        }
    }

    // Slide 5
    Slide {
        anchors.fill: parent
        Image {
            id: slide5
            source: "slide5.png"
            width: parent.width; height: parent.height
            fillMode: Image.PreserveAspectFit
            anchors.centerIn: parent
        }
    }

    function onActivate() {
        presentation.currentSlide = 0;
    }

    function onLeave() {}
}