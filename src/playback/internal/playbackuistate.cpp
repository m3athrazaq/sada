/*
* Audacity: A Digital Audio Editor
*/
#include "playbackuistate.h"

using namespace au::playback;

static const QString PLAYBACK_METER_POSITION_KEY("playbackToolbar/playbackMeterPosition");

void PlaybackUiState::init()
{
    uiState()->uiItemStateChanged(PLAYBACK_METER_POSITION_KEY).onNotify(this, [this]() {
        m_playbackMeterPositionChanged.notify();
    });
}

PlaybackMeterPosition::MeterPosition PlaybackUiState::playbackMeterPosition() const
{
    const QString value = uiState()->uiItemState(PLAYBACK_METER_POSITION_KEY);
    if (value == "1") {
        return PlaybackMeterPosition::MeterPosition::SideBar;
    }
    if (value == "2") {
        return PlaybackMeterPosition::MeterPosition::Bottom;
    }
    return PlaybackMeterPosition::MeterPosition::TopBar;
}

void PlaybackUiState::setPlaybackMeterPosition(PlaybackMeterPosition::MeterPosition position)
{
    QString value = "0";
    if (position == PlaybackMeterPosition::MeterPosition::SideBar) {
        value = "1";
    } else if (position == PlaybackMeterPosition::MeterPosition::Bottom) {
        value = "2";
    }
    if (uiState()->uiItemState(PLAYBACK_METER_POSITION_KEY) == value) {
        return;
    }
    uiState()->setUiItemState(PLAYBACK_METER_POSITION_KEY, value);
}

muse::async::Notification PlaybackUiState::playbackMeterPositionChanged() const
{
    return m_playbackMeterPositionChanged;
}
