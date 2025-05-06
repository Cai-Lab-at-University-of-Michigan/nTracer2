import styled from 'styled-components/macro'
import { useContext, useState, useEffect } from 'react'
import { DashboardContext } from './DashboardReducer'
import { SocketContext } from './Context'
import { useNotification } from './Notification'
import { BASE_URL } from './App'

export default function TracingMenu() {
  const [dashboardState, dashboardDispatch] = useContext(DashboardContext)
  const [zRangeDisplay, setZRangeDisplay] = useState(dashboardState.projection_range)
  const [tracingSpeed, setTracingSpeed] = useState(5)
  const [meanShiftXY, setMeanShiftXY] = useState(10)
  const [meanShiftZ, setMeanShiftZ] = useState(10)
  const socket = useContext(SocketContext)
  const { addNotification } = useNotification()

  useEffect(() => {
    dashboardDispatch({
      type: 'updateAllProperties',
      payload: {
        newState: {
          ...dashboardState,
          tracing_sensitivity: tracingSpeed,
          mean_shift_XY: meanShiftXY,
          mean_shift_Z: meanShiftZ
        }
      }
    })
  }, [tracingSpeed, meanShiftXY, meanShiftZ])

  const changeAction = (action) => {
    fetch(
    "changeAction",
    {
      type:'POST',
      headers: {
        'Content-Type': "application/json",
      },
      body: action,
    });
  };

  const undo = () => {
    socket.emit('undo')
  }

  const redo = () => {
    socket.emit('redo')
  }

  const channelIndexes = []
  for (let c = 0; c < dashboardState.channels; ++c) {
    channelIndexes.push(c)
  }

  const onZLayerChange = (event) => {
    const newZ = parseInt(event.target.value)
    setZRangeDisplay(newZ)
  }

  const setZLayerProjection = () => {
    dashboardDispatch({
      type: 'changeProjectionRange',
      payload: { projection_range: zRangeDisplay }
    })
  }

  const onTraceNeurite = async () => {
    try {
      const response = await fetch(`${BASE_URL}/trace/neurite`);
      const result = await response.json();
      
      if (result.success) {
        // addNotification(result.message || "Neurite traced successfully", "success");
      } else {
        addNotification(result.message || "Failed to trace neurite", "error");
      }
    } catch (error) {
      addNotification("Network error while tracing neurite", "error");
    }
  }

  const onTraceSoma = async () => {
    try {
      const response = await fetch(`${BASE_URL}/trace/soma`);
      const result = await response.json();
      
      if (result.success) {
        // addNotification(result.message || "Soma traced successfully", "success");
      } else {
        addNotification(result.message || "Failed to trace soma", "error");
      }
    } catch (error) {
      addNotification("Network error while tracing soma", "error");
    }
  }

  return (
      <Container>
          <SettingContainer>
            <Subtitle>Adjust tracing sensitivity</Subtitle>
            <SliderContainer>
            <Slider type="range" id="slider" min="1"  max="10" step="1" value={tracingSpeed} onChange={(e) => {setTracingSpeed(parseInt(e.target.value))}}/>
            <SliderValue>{tracingSpeed}</SliderValue>
            </SliderContainer>
          </SettingContainer>
          
          <SettingContainer>
            <Subtitle>Adjust mean shift XY radius</Subtitle>
            <SliderContainer>
            <Slider type="range" id="slider" min="0"  max="20" step="5" value={meanShiftXY} onChange={(e) => {setMeanShiftXY(parseInt(e.target.value))}}/>
            <SliderValue>{meanShiftXY}</SliderValue>
            </SliderContainer>
          </SettingContainer>

          <SettingContainer>
            <Subtitle>Adjust mean shift Z radius</Subtitle>
            <SliderContainer>
            <Slider type="range" id="slider" min="0"  max="20" step="5" value={meanShiftZ} onChange={(e) => {setMeanShiftZ(parseInt(e.target.value))}}/>
            <SliderValue>{meanShiftZ}</SliderValue>
            </SliderContainer>
          </SettingContainer>

          <TraceContainer>
            <TraceHeading>Trace</TraceHeading>
            <TraceButtonContainer>
              <TraceButton onClick={onTraceNeurite}>Neurite</TraceButton>
              <TraceButton onClick={onTraceSoma}>Soma</TraceButton>
            </TraceButtonContainer>
          </TraceContainer>
      </Container>
  )
}

const Container = styled.div`
width: 100%;
`

const Subtitle = styled.h3`
`

const SettingContainer = styled.div`
width: calc(100% - 3rem);
margin-left: 1rem;
`

const SliderContainer = styled.div`
display: flex;
width: 100%;
`

const Slider = styled.input`
flex: 1;
`

const SliderValue = styled.span`
display: flex;
align-items: center;
margin-left: 0.5rem;
font-size: 1.2em;
font-weight: bold;
`

const TraceContainer = styled.div`
width: calc(100% - 5rem);
margin-top: 2rem;
margin-left: 1rem;
padding: 1rem;
border-radius: 5px;
background: rgba(0,0,0,0.05);
`

const TraceHeading = styled.h3`
margin: 0;
margin-bottom: 0.7rem;
padding: 0;
font-size: 1rem;
font-weight: 600;
`

const TraceButtonContainer = styled.div`
display: flex;
`

const TraceButton = styled.button`
cursor: pointer;
font-size: 1.5em;
font-weight: 700;
margin-right: 1rem;
padding: 0.8rem;
border: none;
color: white;
background: #333;
border-radius: 6px;
`