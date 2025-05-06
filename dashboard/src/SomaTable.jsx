import { DashboardContext } from './DashboardReducer'
import { useMemo, useContext, useRef, useEffect } from 'react'
import { useTable } from 'react-table'
import styled from 'styled-components/macro'

export default function SomaTable({ somaList }) {
    const [dashboardState, dashboardDispatch] = useContext(DashboardContext)

    // Track somaList change
    const prevLastSomaRef = useRef(null)

    const data = useMemo(() => {
        if (dashboardState.selected_indexes.length != 1) return []

        return somaList.map((el) => {
            return {
                label: el.neuron + ":" + Math.round(el.z_slice * (1000 / dashboardState.scale[2]))
            }
        })
    }, [somaList, dashboardState.selected_indexes, dashboardState.scale])

    useEffect(() => {
        if (dashboardState.selected_indexes.length === 1 && somaList.length > 0 && dashboardState.selected_point === null) {
            const lastSoma = somaList[somaList.length - 1]
            const prevLastSoma = prevLastSomaRef.current

            if (!prevLastSoma ||
                (prevLastSoma.neuron !== lastSoma.neuron ||
                    prevLastSoma.z_slice !== lastSoma.z_slice)) {

                // Auto-selec
                dashboardDispatch({
                    type: 'somaSelect',
                    payload: {
                        somaSelected: lastSoma.z_slice
                    }
                })
            }
        }

        // Update the ref with the current last soma for the next render
        prevLastSomaRef.current = somaList.length > 0 ?
            { ...somaList[somaList.length - 1] } : null;

    }, [somaList, dashboardDispatch, dashboardState.selected_indexes])

    const columns = useMemo(() => {
        return [
            {
                Header: 'Soma',
                accessor: 'label',
            }
        ]
    }, [])

    const tableInstance = useTable({ columns, data })
    const {
        getTableProps,
        getTableBodyProps,
        headerGroups,
        rows,
        prepareRow,
    } = tableInstance

    const onRowSelect = (z_slice) => {
        const selected = (z_slice == dashboardState.selected_soma_z_slice) ? -1 : z_slice
        dashboardDispatch({
            type: 'somaSelect',
            payload: {
                somaSelected: selected
            }
        })
        // if (i == selectedRow) {
        //     setSelectedRow(-1)
        //     updateViewerState({
        //         selected_soma: -1
        //     })
        // }
        // else {
        //     setSelectedRow(i)
        //     updateViewerState({
        //         selected_soma: somaList[i]['z_slice']
        //     })
        // }
    }

    return (
        <WhiteContainer style={{ width: 195, margin: 0, display: 'flex' }}>
            <table {...getTableProps()} style={{ height: 'fit-content' }}>
                <thead>
                    {// Loop over the header rows
                        headerGroups.map(headerGroup => (
                            // Apply the header row props
                            <HeaderRow {...headerGroup.getHeaderGroupProps()}>
                                {// Loop over the headers in each row
                                    headerGroup.headers.map(column => (
                                        // Apply the header cell props
                                        <th {...column.getHeaderProps()}>
                                            {// Render the header
                                                column.render('Header')}
                                        </th>
                                    ))}
                            </HeaderRow>
                        ))}
                </thead>
                <tbody {...getTableBodyProps()}>
                    {// Loop over the table rows
                        rows.map((row, i) => {
                            // Prepare the row for display
                            prepareRow(row)
                            return (
                                // Apply the row props
                                <TableRow {...row.getRowProps()}
                                    onClick={() => { onRowSelect(somaList[i].z_slice) }}
                                    isSelected={somaList[i].z_slice == dashboardState.selected_soma_z_slice}>
                                    {// Loop over the rows cells
                                        row.cells.map(cell => {
                                            // Apply the cell props
                                            return (
                                                <TableCell {...cell.getCellProps()}>
                                                    {// Render the cell contents
                                                        cell.render('Cell')}
                                                </TableCell>
                                            )
                                        })}
                                </TableRow>
                            )
                        })}
                </tbody>
            </table>
        </WhiteContainer>
    )
}

const WhiteContainer = styled.div`
background-color: #ffffff;
flex: 1;
overflow: auto;
font-size: 0.4em;
border-right: 1px solid #aaa;
/* border-top: 1px solid rgba(0,0,0,0.6); */

th {
  background: rgb(60, 60, 60);
  color: rgba(255, 255, 255, 0.9);
  padding: 0.5rem 0;
  position: sticky;
  top: 0;
  border-left: 1px solid rgb(80, 80, 80);
  margin: 0 0.5rem;
  z-index: 999;
}

table { border: none; border-collapse: collapse; table-layout: fixed; flex: 1}
table td { border-left: 1px solid #000}
table td:first-child { border-left: none; }
table th:first-child { border-left: none; }
`
const HeaderRow = styled.tr`
background: rgb(250,250,250);
`

const TableRow = styled.tr`
background-color: ${(props) => (props.isSelected) ? 'rgb(50, 50, 50)' : 'white'};
color: ${(props) => (props.isSelected) ? 'rgb(230, 230, 230)' : 'rgb(30, 30, 30)'};
:hover {
    background-color: rgb(50, 50, 50);
    color: rgb(230, 230, 230);
}
`

const TableCell = styled.td`
padding: 0.2rem 0.2rem 0.2rem 0.4rem;
`