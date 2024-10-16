import './App.css';
import TopMenu from './TopMenu'
import SideMenu from './SideMenu'
import TreePanel from './TreePanel'
import PointTable from './PointTable'
import SomaTable from './SomaTable'
import Status from './Status'
import {initialDashboardState, DashboardContext, DashboardReducer} from './DashboardReducer'
import { SocketContext } from './Context'
import { useEffect, useState, useReducer, useRef } from 'react'
import styled from 'styled-components/macro'
import { io } from 'socket.io-client';
export const BASE_URL = `http://localhost:${process.env.REACT_APP_SERVER_PORT}`

function App() {
  const [statusMessage, setStatusMessage] = useState('');
  const [data, setData] = useState(null);
  const [pointList, setPointList] = useState([])
  const [somaList, setSomaList] = useState([])
  const updating = useRef(false);
  const [dashboardState, dashboardDispatch] = useReducer(DashboardReducer, initialDashboardState)

  useEffect(() => {
    const evtSource = new EventSource(`${BASE_URL}/stream/dashboard`);
    evtSource.addEventListener("state", ({ data }) => {
      const {dashboard_state, tracing_state, points_state, soma_state} = JSON.parse(data);
      updating.current = true;
      
      dashboardDispatch({
        type: 'updateAllProperties',
        payload: {
          newState: dashboard_state
        }
      })

      setData(tracing_state)
      setPointList(points_state)
      setSomaList(soma_state)
    })
  },[])

  // useEffect(() => {
  //   if (updating.current) {
  //     updating.current = false;
  //     return;
  //   }

  //   socket.emit('update_viewer_state', dashboardState)
  // }, [dashboardState])

  useEffect(()=>{
    // socket.on("status_message", (data) => {
    //   console.log(data)
    //   setStatusMessage(data)
    // })

    // socket.on("downloadSWC", ({ data, filename }) => {
    //   const blob = new Blob([data], { type: 'text/plain' })
    //   const url = window.URL.createObjectURL(blob)
    //   const link = document.createElement('a')
    //   link.setAttribute('href', url)
    //   link.setAttribute('download', filename)
    //   link.style.display = 'none'
    //   document.body.appendChild(link)
    //   link.click()
    //   document.body.removeChild(link)
    // })
  }, [])

  const deleteNeuron = () => {
    fetch(`${BASE_URL}/neuron/delete`)
    // socket.emit('deleteNeuron')
  }

  const deleteBranch = () => {
    fetch(`${BASE_URL}/branch/delete`)
    // socket.emit('deleteBranch')
  }

  const deletePoint = () => {
    fetch(`${BASE_URL}/point/delete`)
    // socket.emit('deletePoint')
  }

  const submitCoordinates = (coordinates) => {
    // fetch(`${BASE_URL}/neuron/delete`)
    // socket.emit('move_to_coordinates', coordinates)
  }

  const completeSoma = () => {
    fetch(`${BASE_URL}/soma/complete`)
    // socket.emit('complete_soma')
  }
  
  return (
    <DashboardContext.Provider value={[dashboardState, dashboardDispatch]}>
      <Container className='App'>
        {/* <TopMenu /> */}
        <LeftContent>
          <Header>
            <HeaderText>nTracer2</HeaderText>
            <HeaderSmallText>v1.0.0-alpha1</HeaderSmallText>
          </Header>
          <MainContainer>
            <LeftContainer padding={5}>
              <WhiteContainer flex={1}>
                {/* <TreeControl>
                  <TreeControlButton onClick={()=>{}}>+</TreeControlButton>
                  <TreeControlButton onClick="clearCurrent(this)">clear</TreeControlButton>
                  <TreeControlButton onClick="fillTree(this)">show</TreeControlButton>
                  <input type="checkbox" onchange="toggleCheckbox(this)" />
                  <br />
                  <br />
                </TreeControl> */}
                <Folders>
                  <TreePanel data={data} />
                </Folders>
              </WhiteContainer>
              <div style={{display: 'flex', overflow: 'scroll', height: '40%', boxShadow: '0px -5px 10px 5px rgba(50, 50, 50, 0.1)' }}>
                <SomaTable somaList={somaList} />
                <PointTable pointList={pointList} />
              </div>
            </LeftContainer>
          </MainContainer>
          {/* <Status statusMessage={statusMessage}/> */}
        </LeftContent>
        <RightContainer>
            <SideMenu deleteNeuron={deleteNeuron}
                      deleteBranch={deleteBranch}
                      deletePoint={deletePoint}
                      submitCoordinates={submitCoordinates}
                      completeSoma={completeSoma} />
        </RightContainer>
      </Container>
    </DashboardContext.Provider>
  );
}

const Container = styled.div`
display: flex;
overflow: hidden;
width: 100vw;
height: 100vh;
`

const LeftContent = styled.div`
height: 100%;
width: calc(100% - 20rem);
`

const MainContainer = styled.div`
display: flex;
position: relative;
height: 100%;
`

const Header = styled.div`
background-color: rgba(0,0,0,0.8);
padding: 0.5rem 0 0.5rem 0.5rem;
`

const HeaderText = styled.h1`
margin: 0;
margin-left: 1rem;
font-weight: 700;
font-size: 1.4em;
color: rgba(0, 0, 0, 0.85);
color: rgba(255, 255, 255, 0.9);
`

const HeaderSmallText = styled.h2`
margin: 0;
margin-left: 1rem;
font-size: 0.85em;
font-weight: 300;
color: rgba(0, 0, 0, 0.8);
color: rgba(255, 255, 255, 0.9);
`

const LeftContainer = styled.div`
display: flex;
flex-direction: column;
flex: 1;
/* border: 1px solid rgba(0, 0, 0, 0.6);
border-radius: 5px; */
/* margin-right: 1rem; */
font-size: 30px;
`

const RightContainer = styled.div`
display: flex;
width: 20rem;
flex-direction: column;
/* border: 1px solid rgba(0, 0, 0, 0.6); */
border-radius: 5px;
font-size: 30px;
padding: 2rem 1rem 1rem 1rem;
box-shadow: -5px 0px 10px 5px rgba(0,0,0,0.1);
z-index: 999;
`

const WhiteContainer = styled.div`
display: flex;
height: 50%;
background-color: #ffffff;
overflow: auto;
padding-bottom: 1rem;
`

const TreeControl = styled.div`
display: flex;
flex-direction: column;
flex-shrink: 1;
border: 1px solid;
text-align: center;
padding: 0.5rem;
`

const TreeControlButton = styled.button`
margin: 0.5rem;
width: 4rem;
`

const Folders = styled.div`
/* border: 1px solid rgba(0, 0, 0, 0.6); */
/* border-radius: 5px; */
text-align: left;
flex: 3;
padding: 0.5rem;
overflow: auto;
`

const SomaContainer = styled.div`
display: flex;
flex-shrink: 1;
background-color: #ffffff;
overflow: auto;
`

export default App;
