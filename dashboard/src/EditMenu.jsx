import './App.css';
import { useState, useContext } from 'react'
import { SocketContext } from './Context'
import { DashboardContext } from './DashboardReducer'
import { useNotification } from './Notification'
import styled from 'styled-components/macro'
import { BASE_URL } from './App'

export default function EditMenu({ deleteNeuron, deleteBranch, deletePoint, submitCoordinates, completeSoma }) {
  const [x, setX] = useState(null);
  const [y, setY] = useState(null);
  const [z, setZ] = useState(null);
  const { addNotification } = useNotification();
  const [dashboardState, dashboardDispatch] = useContext(DashboardContext)

  const onSubmitCoordinates = () => {
    if (!x || !y || !z) {
      return;
    }

    submitCoordinates([x, y, z]);
  }

  const onDeleteNeuron = async () => {
    try {
      const response = await fetch(`${BASE_URL}/neuron/delete`);
      const result = await response.json();
      
      if (result.success) {
        addNotification(result.message || "Neuron deleted successfully", "success");
      } else {
        addNotification(result.message || "Failed to delete neuron", "error");
      }
    } catch (error) {
      addNotification("Network error while deleting neuron", "error");
    }
  }

  const onDeleteSoma = async () => {
    try {
      const response = await fetch(`${BASE_URL}/soma/delete`);
      const result = await response.json();
      
      if (result.success) {
        addNotification(result.message || "Soma deleted successfully", "success");
      } else {
        addNotification(result.message || "Failed to delete soma", "error");
      }
    } catch (error) {
      addNotification("Network error while deleting soma", "error");
    }
  }

  const onNeuronCombine = async () => {
    try {
      const response = await fetch(`${BASE_URL}/neuron/combine`);
      const result = await response.json();
      
      if (result.success) {
        addNotification(result.message || "Neurons combined successfully", "success");
      } else {
        addNotification(result.message || "Failed to combine neurons", "error");
      }
    } catch (error) {
      addNotification("Network error while combining neurons", "error");
    }
  }

  const onExpandAll = () => {
    dashboardDispatch({
      type: 'treeExpandAll'
    });
  }

  const onCollapseAll = () => {
    dashboardDispatch({
      type: 'treeCollapseAll'
    });
  }

  const onBranchBreak = async () => {
    try {
      const response = await fetch(`${BASE_URL}/branch/break`);
      const result = await response.json();
      
      if (result.success) {
        addNotification(result.message || "Branch broken successfully", "success");
      } else {
        addNotification(result.message || "Failed to break branch", "error");
      }
    } catch (error) {
      addNotification("Network error while breaking branch", "error");
    }
  }

  const onSetPrimaryBranch = async () => {
    try {
      const response = await fetch(`${BASE_URL}/branch/set_primary`);
      const result = await response.json();
      
      if (result.success) {
        addNotification(result.message || "Primary branch set successfully", "success");
      } else {
        addNotification(result.message || "Failed to set primary branch", "error");
      }
    } catch (error) {
      addNotification("Network error while setting primary branch", "error");
    }
  }

  const onJoinBranch = async () => {
    try {
      const response = await fetch(`${BASE_URL}/branch/join`);
      const result = await response.json();
      
      if (result.success) {
        addNotification(result.message || "Branches joined successfully", "success");
      } else {
        addNotification(result.message || "Failed to join branches", "error");
      }
    } catch (error) {
      addNotification("Network error while joining branches", "error");
    }
  }

  const onDeleteBranch = async () => {
    try {
      const result = await deleteBranch();
      if (result && result.success) {
        addNotification(result.message || "Branch deleted successfully", "success");
      } else if (result) {
        addNotification(result.message || "Failed to delete branch", "error");
      }
    } catch (error) {
      addNotification("Network error while deleting branch", "error");
    }
  }

  const onDeletePoint = async () => {
    try {
      const result = await deletePoint();
      if (result && result.success) {
        addNotification(result.message || "Point deleted successfully", "success");
      } else if (result) {
        addNotification(result.message || "Failed to delete point", "error");
      }
    } catch (error) {
      addNotification("Network error while deleting point", "error");
    }
  }

  const onCompleteSoma = async () => {
    try {
      const result = await completeSoma();
      if (result && result.success) {
        addNotification(result.message || "Soma completed successfully", "success");
      } else if (result) {
        addNotification(result.message || "Failed to complete soma", "error");
      }
    } catch (error) {
      addNotification("Network error while completing soma", "error");
    }
  }

  return (
    <>
      <FlexContainer>
        <Column>
          <Subtitle>Branch</Subtitle>
          <BorderContainer width={4}>
            <MediumButton onClick={onSetPrimaryBranch}>Set Primary</MediumButton>
            <br />
            <MediumButton onClick={onJoinBranch}>Join</MediumButton>
            <br />
            <MediumButton onClick={onBranchBreak}>Break</MediumButton>
          </BorderContainer>
          <Subtitle>Neuron</Subtitle>
          <BorderContainer width={4}>
            <MediumButton onClick={onNeuronCombine}>Combine Multiple</MediumButton>
            <br />
            {/* <SmallButton onClick={onExpandAll}>Exapand All</SmallButton>
            <br />
            <SmallButton onClick={onCollapseAll}>Collapse All</SmallButton> */}
          </BorderContainer>
          {/* <Subtitle>JumpTo Next</Subtitle>
          <BorderContainer>
            <LargeButton style={{marginTop: 10}}>Incomplete</LargeButton>
            <br />
            <LargeButton>Selected</LargeButton>
            <br />
            <LargeButton>Synapse</LargeButton>
            <br />
            <LargeButton>Connected</LargeButton>
          </BorderContainer> */}
        </Column>
        <Column>
          <Subtitle>Delete</Subtitle>
          <BorderContainer width={4.2}>
            <MediumButton onClick={onDeleteBranch}>1 Branch</MediumButton>
            <br />
            <MediumButton onClick={onDeleteNeuron}>Neuron</MediumButton>
            <br />
            <MediumButton onClick={onDeleteSoma}>Soma</MediumButton>
            <br />
            <MediumButton onClick={onDeletePoint}>Point</MediumButton>
          </BorderContainer>
          <div className="fixed" style={{marginLeft: 5}}>
            <Subtitle>Soma</Subtitle>
            <BorderContainer width={4.2}>
              <MediumButton onClick={onCompleteSoma}>Complete</MediumButton>
            </BorderContainer>
            {/* <Subtitle>Synapse</Subtitle>
            <BorderContainer width={4.2}>
              <MediumButton>Type +</MediumButton>
              <MediumButton>Type -</MediumButton>
            </BorderContainer>
            <Subtitle>Connection</Subtitle>
            <BorderContainer width={4.2}>
              <MediumButton>+ / -</MediumButton>
              <MediumButton>GOTO</MediumButton>
            </BorderContainer> */}
          </div>
        </Column>
      </FlexContainer>   
      {/* <Subtitle>Coordinate Selection</Subtitle>
      <BorderContainer width={167} style={{paddingTop: 10, paddingBottom: 10, textAlign: 'center'}}>
        <span>X Coordinate</span>
        <CoordinateInput type="number" id="x_coordinate" onChange={(evt)=>setX(evt.target.value)}/>
        <br />
        <span>Y Coordinate</span>
        <CoordinateInput type="number" id="y_coordinate" onChange={(evt)=>setY(evt.target.value)}/>
        <br />
        <span>Z Coordinate</span>
        <CoordinateInput type="number" id="z_coordinate" onChange={(evt)=>setZ(evt.target.value)}/>
        <br />
        <br />
        <button id="submission" onClick={onSubmitCoordinates} type="button" >Submit Coordinates</button>   
      </BorderContainer> */}
    </>
  )
}

const Subtitle = styled.h3`
margin: 1rem 0 0.25rem 0.8rem;
font-weight: 300;
font-size: 1.1rem;
`

const FlexContainer = styled.div`
  display: flex;
  flex: 1;
  width: 100%;
  align-items: stretch;
`

const SmallButton = styled.button`
width: 70px;
margin-bottom: 0.3rem;
`

const MediumButton = styled.button`
width: 100%;
margin-bottom: 0.3rem;
font-size: 1.3em;
font-weight: 800;
color: rgba(0,0,0,0.8);
background-color: rgba(0,0,0,0.1);
border: none;
padding: 0.7rem;
border-radius: 5px;
cursor: pointer;
`

const LargeButton = styled.button`
width: 76px;
margin-bottom: 0.3rem;
`

const BorderContainer = styled.div`
border-radius: 5px;
margin: 0.3rem;
margin-top: 0;
padding: 0.5rem;
padding-top: 0.7rem;
align-items: center;
text-align: center;
`

const CoordinateInput = styled.input`
margin-left: 10px;
`
const Column = styled.div`
flex: 1;
:first-child {
  margin-right: 10px;
}
`