import styled from 'styled-components/macro'
import { useContext, useState, useEffect } from 'react'
import { DashboardContext } from './DashboardReducer'
import { SocketContext } from './Context'
import { BASE_URL } from './App'

export default function TracingMenu() {
  const [dashboardState, dashboardDispatch] = useContext(DashboardContext)
  const [zRangeDisplay, setZRangeDisplay] = useState(dashboardState.projection_range)
  const [tracingSpeed, setTracingSpeed] = useState(5)
  const [meanShiftXY, setMeanShiftXY] = useState(10)
  const [meanShiftZ, setMeanShiftZ] = useState(10)
  const socket = useContext(SocketContext)

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

  // const channelDisplayButtons = channelIndexes.map(channel => {
  //   const checkboxId = `a${channel}`
  //   const onChange = (e) => {
  //     dashboardDispatch({
  //       type: 'toggleDisplayChannel',
  //       payload: { channel }
  //     })
  //   }

  //   return (
  //     <>
  //     <input type="checkbox"
  //            style={{marginTop:-1}}
  //            id={checkboxId}
  //            checked={dashboardState.selected_display_channels.includes(channel)}
  //            onChange={onChange}
  //            />
  //     <label for={checkboxId}>{channel}</label>
  //     </>
  //   )
  // })

  // const channelAnalysisButtons = channelIndexes.map(channel => {
  //   const checkboxId = `a${channel}`
  //   const onChange = (e) => {
  //     dashboardDispatch({
  //       type: 'toggleAnalysisChannel',
  //       payload: { channel }
  //     })
  //   }

  //   return (
  //     <>
  //     <input type="checkbox"
  //            style={{marginTop:-1}}
  //            id={checkboxId}
  //            checked={dashboardState.selected_analysis_channels.includes(channel)}
  //            onChange={onChange}
  //            />
  //     <label for={checkboxId}>{channel}</label>
  //     </>
  //   )
  // })

  // const onZLayerChange = (event) => {
  //   const newZ = parseInt(event.target.value)
  //   setZRangeDisplay(newZ)
  // }

  useEffect(() => {
      setZLayerProjection();
  }, [zRangeDisplay]);

  const setZLayerProjection = () => {
    dashboardDispatch({
      type: 'changeProjectionRange',
      payload: { projection_range: zRangeDisplay }
    })
  }

  const onTraceNeurite = async () => {
    fetch(`${BASE_URL}/trace/neurite`)
  }

  const onTraceSoma = async () => {
    fetch(`${BASE_URL}/trace/soma`)
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

          <SettingContainer>
              <Subtitle>Adjust number of projected Z slices</Subtitle>
              <SliderContainer>
              <Slider type="range" id="slider" min={dashboardState.min_projection_slice}  max={meanShiftZ * 2} step="1" value={zRangeDisplay} onChange={(e) => {setZRangeDisplay(parseInt(e.target.value))}}/>
              <SliderValue>{zRangeDisplay}</SliderValue>
              </SliderContainer>
          </SettingContainer>

          <TraceContainer>
            <TraceHeading>Trace</TraceHeading>
            <TraceButtonContainer>
              <TraceButton onClick={onTraceNeurite}>Neurite</TraceButton>
              <TraceButton onClick={onTraceSoma}>Soma</TraceButton>
            </TraceButtonContainer>
          </TraceContainer>

          {/* <FlexContainer>
              <div class="fixed">
                  <h3 class="subtitle">Tracing</h3>
                  <div class="border" style={{width: 65}}>
                      <List>
                          <input type="radio" id="interactive" name="tracing" value="interactive" checked="checked" />
                          <label for="interactive">Interactive</label><br />
                          <input type="radio" id="semi-auto" name="tracing"  value="interactive" />
                          <label for="semi-auto">Semi-Auto</label><br />
                      </List>
                  </div>
              </div>
              <div class="fixed">
                  <h3 class="subtitle" style={{marginLeft:10}}>Labeling</h3>
                  <BorderContainer style={{width:50, marginLeft:10}}>
                      <List>
                          <input type="radio" id="memb" name="labeling" value="memb" checked="checked" />
                          <label for="memb">Memb</label><br />
                          <input type="radio" id="cyto" name="labeling" value="cyto" />
                          <label for="cyto">Cyto</label><br />
                      </List>
                  </BorderContainer>
              </div>
          </FlexContainer> */}

          {/* <h3 class="subtitle">Sampling Radius (pixels)</h3>
          <BorderContainer style={{display: "flex", paddingTop:10, paddingBottom:10, marginBottom:10}}>
              <label for="xy" style={{marginTop:5, marginRight:5}}> X, Y</label>
              <input type="number" />
              <label for="z" style={{marginTop:5, marginRight:5, marginLeft:10}}>Z</label>
              <input type="number" />
          </BorderContainer>

          <h3 class="subtitle">Sampling Tolerance</h3>
          <BorderContainer style={{display: "flex", paddingTop:10, paddingBottom:10, marginBottom:10}}>
              <label for="color" style={{marginTop:5, marginRight:5, marginLeft:-5}}>Color</label>
              <input type="number" />
              <label for="int" style={{marginTop:5, marginRight:5, marginLeft:10}}>Int</label>
              <input type="number" />
          </BorderContainer>

          <button style={{fontSize:11, textAlign: "center", marginBottom:10}}>Change "completeness"</button>
          <button style={{fontSize:11, textAlign: "center"}}>Clear Start/End Points</button>

          <Subtitle>Trace!</Subtitle> */}
        {/* <BorderContainer style={{display: "flex", paddingTop:10, paddingBottom:10, marginBottom:10}}>
          <button>Neurite</button>
          <div style={{marginLeft:10}}>
            <button style={{width: 50}}>Soma</button>
            <br />
            <br />
            <button style={{width: 50}}>Spine</button>
          </div>
        </BorderContainer> */}

        {/* <h3 class="subtitle">Channel</h3>
        <BorderContainer>
          <div style={{display: "flex", marginTop:10}}>
            <div style={{marginRight:18}}>Display</div>
            {channelDisplayButtons}
          </div>

          <div style={{display: "flex", marginTop:10}}>
            <div style={{marginRight:18}}>Analysis</div>
            {channelAnalysisButtons}
          </div>

          <div style={{display: "flex", marginTop:10}}>
            <div style={{marginRight:25}}>Toggle</div>
            <input type="checkbox" style={{marginTop:-1}} />
            <label for="a1">1</label>
            <input type="checkbox" style={{marginTop:-1}} />
            <label for="a2">2</label>
            <input type="checkbox" style={{marginTop:-1}} />
            <label for="a3">3</label>
          </div>
          <div style={{display: "flex", marginTop:10}}>
            <div style={{marginRight:0}}>Toggle Color</div>
            <input type="radio" style={{marginTop:-1}} />
            <label for="a1">1</label>
            <input type="radio" style={{marginTop:-1}} />
            <label for="a2">2</label>
            <input type="radio" style={{marginTop:-1}} />
            <label for="a3">3</label>
          </div>
        </BorderContainer> */}

        {/* <Subtitle>Functions</Subtitle>
        <BorderContainer>
          <br />
          <button id="selectors" onClick={()=>changeAction('first point')}>First Point</button>
          <br />
          <button id="selectors" onClick={()=>changeAction('second point')}>Second Point</button>
          <br />
          <button id="selectors" onClick={undo}>Undo</button>
          <button id="selectors" onClick={redo}>Redo</button>
          <br />
          <button id="selectors" onClick={()=>changeAction('thick')}>Thick</button>
          <br />
          <button id="selectors" onClick={()=>changeAction('thin')}>Thin</button>
          <br />
          <button id="selectors" onClick={()=>changeAction('branch')}>Branch</button>
          <br />
          <button id="selectors" onClick={()=>changeAction('increase brightness')}>Increase Brightness</button>
          <br />
          <button id="selectors" onClick={()=>changeAction('decrease brightness')}>Decrease Brightness</button>
          <br />
          <button id="selectors" onClick={()=>changeAction('translate-via-mouse-drag')}>Default</button>
          <br />
          <br />
        </BorderContainer> */}
      </Container>
  )
}

const Container = styled.div`
width: 100%;
`

const FlexContainer = styled.div`
  display: flex;
`

const Subtitle = styled.h3`
`

const BorderContainer = styled.div`
border: 1px solid #ccc;
margin-top: -18px;
padding-left: 10px;
`

const List = styled.ol`
  margin-left: -40px;
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