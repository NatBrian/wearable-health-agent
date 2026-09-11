package dev.wha.app.ui.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dev.wha.app.core.ErrorKind
import dev.wha.app.core.WhaCore
import dev.wha.app.core.WhaResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class HistoryUiState(
    val nights: List<NightSummary> = emptyList(),
    val episodes: Map<String, dev.wha.app.core.EpisodeSummary> = emptyMap(),
    val showTable: Boolean = false,
    val error: WhaResult.Err? = null,
)

class HistoryViewModel(private val core: WhaCore, private val subject: String) : ViewModel() {
    private val _state = MutableStateFlow(HistoryUiState())
    val state: StateFlow<HistoryUiState> = _state

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            val nights = try {
                core.nights(subject, 60)
            } catch (e: Exception) {
                WhaResult.Err(ErrorKind.INTERNAL, "${e::class.simpleName}: ${e.message}")
            }
            when (nights) {
                is WhaResult.Err -> {
                    _state.value = HistoryUiState(error = nights)
                    return@launch
                }
                is WhaResult.Ok -> {
                    val episodes = try {
                        core.episodes(subject)
                    } catch (e: Exception) {
                        null
                    }
                    val byId = (episodes as? WhaResult.Ok)?.value?.associateBy { it.episode_id } ?: emptyMap()
                    _state.value = HistoryUiState(
                        nights = nights.value.sortedByDescending { it.night_date }.map {
                            NightSummary(
                                night_date = it.night_date,
                                rhr_bpm = it.rhr_bpm,
                                band_lo = it.band_lo,
                                band_hi = it.band_hi,
                                level = it.level,
                                usable = it.usable,
                                coverage_minutes = it.coverage_minutes,
                                episode_id = it.episode_id,
                                deviation_bpm = it.deviation_bpm,
                            )
                        },
                        episodes = byId,
                    )
                }
            }
        }
    }

    fun toggleTable(show: Boolean) {
        _state.value = _state.value.copy(showTable = show)
    }
}
