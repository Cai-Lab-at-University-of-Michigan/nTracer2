import { useMemo, useContext, useRef, useEffect } from 'react'
import { DashboardContext } from './DashboardReducer'
import { useTable, useBlockLayout } from 'react-table'
import styled from 'styled-components/macro'

export default function PointTable({ pointList }) {
    const [dashboardState, dashboardDispatch] = useContext(DashboardContext)

    const data = useMemo(() => {
        return pointList.map((el) => {
            return {
                type: el.type,
                x: el.x,
                y: el.y,
                z: el.z,
                display_x: Math.round(el.x * (1000 / dashboardState.scale[0])),
                display_y: Math.round(el.y * (1000 / dashboardState.scale[1])),
                display_z: Math.round(el.z * (1000 / dashboardState.scale[2])),
                radius: el.r,
                synapse: 0,
                connection: "0.0"
            }
        })
    }, [pointList])

    const selectedRowIndex = useMemo(() => {
        if (!dashboardState.selected_point) return -1
        
        for (const [i, row] of pointList.entries()) {
            if (row.x == dashboardState.selected_point[0]
                && row.y == dashboardState.selected_point[1]
                && row.z == dashboardState.selected_point[2]) {
                    return i
            }
        }

        return -1
    }, [dashboardState.selected_point, pointList])

    // Track pointList change
    const prevLastPointRef = useRef(null)

    useEffect(() => {
        if (pointList.length > 0) {
            const lastPoint = pointList[pointList.length - 1]
            const prevLastPoint = prevLastPointRef.current
            
            if (!prevLastPoint || 
                (prevLastPoint.x !== lastPoint.x || 
                 prevLastPoint.y !== lastPoint.y || 
                 prevLastPoint.z !== lastPoint.z || 
                 prevLastPoint.type !== lastPoint.type ||
                 prevLastPoint.r !== lastPoint.r)) {
                
                // Auto-select
                dashboardDispatch({
                    type: 'tableSelect',
                    payload: {
                        pointSelected: [lastPoint.x, lastPoint.y, lastPoint.z]
                    }
                })
            }
        }

        prevLastPointRef.current = pointList.length > 0 ? 
            { ...pointList[pointList.length - 1] } : null;
            
    }, [pointList, dashboardDispatch])

    useEffect(() => {
        if (!!document) {
            // const selectedRow = document.getElementById(`pointrow-${selectedRowIndex}`)
            // fix id mismatch so that auto scroll works
            const selectedRow = document.getElementById(rows[selectedRowIndex]?.id)
            if (!!selectedRow) {
                const rect = selectedRow.getBoundingClientRect()
                const isInView = rect.top >= 0 && rect.bottom <= window.innerHeight
                if (!isInView) {
                    selectedRow.scrollIntoView({ block: "nearest" })
                    selectedRow.focus()
                }
            }
        }
    }, [selectedRowIndex, rows])

    const onRowSelect = (i) => {
        let xyz = null
        if (i != selectedRowIndex) {
            const selectedRow = pointList[i]
            xyz = [selectedRow.x, selectedRow.y, selectedRow.z]
        }

        dashboardDispatch({
            type: 'tableSelect',
            payload: {
                pointSelected: xyz
            }
        })
    }

    const onTableKey = (event, i, rowId) => {
        if (selectedRowIndex == -1) return

        event.stopPropagation()
        event.preventDefault()
        const currentRow = tBodyRef.current?.children.namedItem(rowId);

        if (!currentRow) return

        switch (event.key) {            
            case "ArrowUp": 
              if (i == 0) return
              currentRow.previousElementSibling.focus();
              onRowSelect(i - 1)
              break;      
            case "ArrowDown": 
              if (i == pointList.length - 1) return
              currentRow.nextElementSibling.focus();
              onRowSelect(i + 1)
              break;  
            default: break;
        }
    }

    const columns = useMemo(() => {
        return [
            {
                Header: 'Type',
                accessor: 'type',
            },
            {
                Header: 'X',
                accessor: 'display_x',
            },
            {
                Header: 'Y',
                accessor: 'display_y',
            },
            {
                Header: 'Z',
                accessor: 'display_z',
            },
            {
                Header: 'Radius',
                accessor: 'radius',
            },
            {
                Header: 'Synapse?',
                accessor: 'synapse',
            },
            {
                Header: 'Connection',
                accessor: 'connection',
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

    const tBodyRef = useRef(null)

    return (
        <WhiteContainer style={{width: 195, margin: 0, display: 'flex'}}>
        <table {...getTableProps()} style={{height: 'fit-content'}}>
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
            <tbody {...getTableBodyProps()} ref={tBodyRef}>
            {// Loop over the table rows
            rows.map((row, i) => {
                // Prepare the row for display
                prepareRow(row)
                return (
                // Apply the row props
                <TableRow {...row.getRowProps()}
                id={row.id}
                tabIndex={0}
                onClick={() => {onRowSelect(i)}}
                onKeyDown={(e) => onTableKey(e, i, row.id)}
                isSelected={i == selectedRowIndex}>
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
flex: 4;
overflow: auto;
font-size: 0.4em;

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
table td { border-left: 1px solid rgb(150, 150, 150);}
table td:first-child { border-left: none; }
table th:first-child { border-left: none; }
`
const HeaderRow = styled.tr`
background: rgb(250,250,250);
`

const TableRow = styled.tr`
background-color: white;
color: rgb(30, 30, 30);
:hover {
    background-color: rgba(50, 50, 50, 0.1);
    color: black;
}
${(props)=>(props.isSelected) && 'background-color: rgb(50, 50, 50) !important;'}
${(props)=>(props.isSelected) && 'color: rgb(230, 230, 230) !important;'}
`

const TableCell = styled.td`
padding: 0.2rem 0.2rem 0.2rem 0.4rem;
`