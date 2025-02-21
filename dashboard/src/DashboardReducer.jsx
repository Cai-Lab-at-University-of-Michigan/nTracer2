import React from 'react'
import { BASE_URL } from './App'

export const DashboardContext = React.createContext()

export const initialDashboardState = {
    selected_indexes: [],
    expanded_neuron: -1,
    selected_soma_z_slice: -1,
    selected_point: null,
    highlight_all: false,
    highlight_selected: true,
    tree_expand_all: false,
    channels: 0,
    selected_display_channels: [],
    selected_analysis_channels: [],
    projection_range: 10,
    min_projection_slice: 1,
    max_projection_slice: 100,
    scale: [1, 1, 1],
    tracing_sensitivity: 5,
    mean_shift_XY: 5,
    mean_shift_Z: 5
}

const send_dashboard_state_update = (dashboardState) => {
    fetch(`${BASE_URL}/dashboard_state/update`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(dashboardState)
    })
}

export const DashboardReducer = (state, action) => {
    let newState;
    switch (action.type) {
        case 'treeSelect':
            let selection = []
            if (action.payload.selection) {
                selection = action.payload.selection.map(
                    selected => selected.split('-').map(s => parseInt(s))
                )
            }
            
            if (selection == state.selected_indexes) return state

            newState = {
                ...state,
                selected_indexes: selection,
                selected_soma_z_slice: -1,
                selected_point: null
            }

            send_dashboard_state_update(newState)
            return newState
        case 'treeExpandAll':
            newState = {
                ...state,
                tree_expand_all: true
            }
            send_dashboard_state_update(newState)
            return newState
        case 'treeCollapseAll':
            newState = {
                ...state,
                tree_expand_all: false
            }
            send_dashboard_state_update(newState)
            return newState
        case 'tableSelect':
            const pointSelected = action.payload.pointSelected
            if (state.selected_point == pointSelected) return state

            newState = {
                ...state,
                selected_point: pointSelected
            }
            send_dashboard_state_update(newState)
            return newState
        case 'somaSelect':
            const somaSelected = action.payload.somaSelected
            newState = {
                ...state,
                selected_soma_z_slice: somaSelected
            }
            send_dashboard_state_update(newState)
            return newState
        case 'setHighlightAll':
            newState = {
                ...state,
                highlight_all: action.payload.highlightAll
            }
            send_dashboard_state_update(newState)
            return newState
        case 'setHighlightSelected':
            newState = {
                ...state,
                highlight_selected: action.payload.highlightSelected
            }
            send_dashboard_state_update(newState)
            return newState
        case 'updateAllProperties':
            return action.payload.newState
        case 'toggleDisplayChannel':
            if (state.selected_display_channels.includes(action.payload.channel)) {
                newState = {
                    ...state,
                    selected_display_channels: state.selected_display_channels.filter(e => e != action.payload.channel)
                }
            } else {
                newState = {
                    ...state,
                    selected_display_channels: [...state.selected_display_channels, action.payload.channel]
                }
            }
            send_dashboard_state_update(newState)
            return newState
        case 'toggleAnalysisChannel':
            if (state.selected_analysis_channels.includes(action.payload.channel)) {
                newState = {
                    ...state,
                    selected_analysis_channels: state.selected_analysis_channels.filter(e => e != action.payload.channel)
                }
            } else {
                newState = {
                    ...state,
                    selected_analysis_channels: [...state.selected_analysis_channels, action.payload.channel]
                }
            }
            send_dashboard_state_update(newState)
            return newState
        case 'changeProjectionRange':
            newState = {
                ...state,
                projection_range: action.payload.projection_range
            }
            send_dashboard_state_update(newState)
            return newState
        case 'setExpandedNeuron':
            newState = {
                ...state,
                expanded_neuron: action.payload.expanded_neuron
            }
            send_dashboard_state_update(newState)
            return newState
        case 'unselectPoint':
            newState = {
                ...state,
                selected_point: null,
                selected_indexes: []
            }
            send_dashboard_state_update(newState)
            return newState
        case 'setSelectedIndexes':
            newState = {
                ...state,
                selected_indexes: action.payload.selected_indexes
            }
            send_dashboard_state_update(newState)
            return newState
        default:
            return state
    }
}