/*
* Sada: a full-width, horizontal playback level meter docked below the editor
* (used when the meter position is "Bottom").
*/
import QtQuick
import QtQuick.Layouts

import Muse.Ui
import Muse.UiComponents

import Audacity.Playback 1.0

Item {
    id: root

    property alias navigationSection: navPanel.section
    property alias navigationOrderStart: navPanel.order

    NavigationPanel {
        id: navPanel

        name: "LevelsPanel"
        enabled: root.enabled && root.visible
        direction: NavigationPanel.Horizontal

        accessible.name: qsTrc("playback", "Levels")
    }

    PlaybackMeterPanelModel {
        id: model

        onIsPlayingChanged: {
            if (model.isPlaying) {
                leftVolumePressure.reset()
                leftVolumePressure.resetClipped()
                rightVolumePressure.reset()
                rightVolumePressure.resetClipped()
            }
        }
    }

    Component.onCompleted: {
        model.init()
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 12
        spacing: 8

        FlatButton {
            id: meterOptionsBtn

            Layout.preferredWidth: 28
            Layout.preferredHeight: 28
            Layout.alignment: Qt.AlignVCenter

            icon: IconCode.AUDIO
            //: Tooltip of the playback meter settings button
            toolTipTitle: qsTrc("playback", "Playback meter settings")
            accentButton: popup.isOpened

            navigation.name: "LevelsSettings"
            navigation.panel: navPanel
            navigation.order: 1

            onClicked: {
                popup.toggleOpened()
            }

            PlaybackMeterCustomisePopup {
                id: popup

                placementPolicies: PopupView.PreferAbove

                model: model.meterModel
            }
        }

        Item {
            id: meterArea

            Layout.fillWidth: true
            Layout.fillHeight: true

            Column {
                id: meterColumn

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter

                spacing: 2

                HorizontalVolumePressureMeter {
                    id: leftVolumePressure

                    x: ruler.x + ruler.leftTextMargin
                    width: ruler.effectiveWidth + leftVolumePressure.overloadTotalSpace
                    height: 8

                    meterModel: model.meterModel
                    currentVolumePressure: model.leftChannelPressure
                    currentRMS: model.leftChannelRMS
                }

                HorizontalVolumePressureMeter {
                    id: rightVolumePressure

                    x: ruler.x + ruler.leftTextMargin
                    width: ruler.effectiveWidth + leftVolumePressure.overloadTotalSpace
                    height: 8

                    meterModel: model.meterModel
                    currentVolumePressure: model.rightChannelPressure
                    currentRMS: model.rightChannelRMS
                }

                HorizontalVolumePressureRuler {
                    id: ruler

                    meterModel: model.meterModel

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.rightMargin: leftVolumePressure.overloadWidth
                }
            }

            MouseArea {
                anchors.fill: meterColumn

                // Clicking the meter clears the peak and clip indicators
                onClicked: {
                    leftVolumePressure.reset()
                    leftVolumePressure.resetClipped()
                    rightVolumePressure.reset()
                    rightVolumePressure.resetClipped()
                }
            }
        }
    }
}
