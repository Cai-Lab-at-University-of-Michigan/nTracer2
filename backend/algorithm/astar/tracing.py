from time import time

from math import floor, ceil
import multiprocessing
import requests
import posixpath
# cimport numpy as np
from algorithm.astar.AstarWrapper import AstarWrapper as Astar

def get_trace_cdn(server_url: str, dataset_id: str, start, end, is_multi, is_soma = False, xy_extension = 21, z_extension = 7, rScale = 10, seg_len = 25, tracing_sensitivity = 5):
    url = posixpath.join(server_url, dataset_id, "tracing", f"{start[0]},{start[1]},{start[2]}", f"{end[0]},{end[1]},{end[2]}")
    res = requests.get(url, params={"is_soma": "true" if is_soma else "false"})
    if res.status_code == 200:
        return [[int(p) for p in x.split(',')] for x in res.text.split('\n')[:-1]]
    else:
        raise Exception(f"[{res.status_code}] {res.text}")


def get_trace(coords, start, end, is_multi, is_soma = False, xy_extension = 21, z_extension = 7, rScale = 10, seg_len = 25, tracing_sensitivity = 5):
    # manager = multiprocessing.Manager()
    # rtrn = manager.dict()

    dist = abs(start[0] - end[0]) + abs(start[1] - end[1]) + abs(start[2] - end[2])
    # res_index = min(int((dist ** 0.5) // rScale), 5) if is_multi is False else 0

    # p = multiprocessing.Process(target = traceThread, name = "Trace", args = (rtrn, "Trace", coords, start, end, is_soma, xy_extension, z_extension, res_index, seg_len, tracing_sensitivity, is_multi, False))
    # p.start()
    # p.join(15)
    tracer = Astar(is_soma, xy_extension, z_extension, tracing_sensitivity, is_multi)
    res = tracer.get_trace(start, end, coords.layer_data[0])
    return res

    # if len(multiprocessing.active_children()) > 1 or not("Trace" in rtrn):
    #     print("Timed out of astar trace")
    #     for t, x in enumerate(multiprocessing.active_children()):
    #         if x.name == "Trace" or len(x.name) < 4:
    #             x.terminate()
    #             x.join()
    #     return []
    # else:
    #     print("Astar finished")
    #     print("Trace length: ", len(rtrn['Trace']))
    #     return rtrn['Trace']
    # return astar_single_channel(coords.imPath, start, end, is_soma, xy_extension, z_extension)


def traceThread(rtrn, name, coords, start, end, is_soma, xy_extension, z_extension, res, seg_len, tracing_sensitivity, is_multi, thread_ind = False):
    return
    if is_multi:
        tracer = AstarMulti(start, end, coords, is_soma, xy_extension, z_extension, res, tracing_sensitivity=tracing_sensitivity)
    else:
        tracer = AstarSingle(start, end, coords, is_soma, xy_extension, z_extension, res, tracing_sensitivity=tracing_sensitivity)
    t1 = time()
    path = tracer.get_trace()
    t2 = time()
    print("Astar time: ", t2 - t1)
    
    if len(path) == 0: return

    if res > 0:
        print("low res found")
        path_length = len(path)
        trace_count = max(2, ceil(path_length * (pow(2, res)) / seg_len))
        
        trace_index = ceil(path_length / trace_count)

        ongoing_traces = []

        for i in range(trace_count):
            start_index = int(i * trace_index)
            end_index = min(int((i + 1) * trace_index), path_length - 1)

            if(start_index >= len(path)):
                break

            start_coords = tuple([path[start_index][0], path[start_index][1], path[start_index][2]])
            end_coords = tuple([path[end_index][0], path[end_index][1], path[end_index][2]])

            start_coords = mean_shift(coords, start_coords, is_multi, 2, pow(2, res))
            end_coords = mean_shift(coords, end_coords, is_multi, 2, pow(2, res))

            ongoing_traces.append(multiprocessing.Process(target = traceThread, name = " sub" + str(i), args = (rtrn, str(i), coords, start_coords, end_coords, is_soma, xy_extension, z_extension, 0, seg_len, tracing_sensitivity, is_multi)))
            ongoing_traces[i].start()
    
        for trace in ongoing_traces:
            trace.join(10)
            if trace.is_alive(): return

        path = []
        for i in range(trace_count):
            if not(str(i) in rtrn): 
                return
            path += rtrn[str(i)]
            if thread_ind:
                segment = rtrn[str(i)][-1]
                segment[1] += 10
                path += [segment]
        rtrn[name] = path
        print("threads: ", trace_count)
        return

    rtrn[name] = path


# def astar_color(img, start, end, is_soma=False, xy_extension=21, z_extension=7):
#     cython.declare(minX0=cython.int, minX1=cython.int, minX2=cython.int, maxX0=cython.int, maxX1=cython.int, maxX2=cython.int)
#     cython.declare(offset0=cython.int, offset1=cython.int, offset2=cython.int)

#     minX0, minX1, minX2 = min(start[0], end[0]), min(start[1], end[1]), min(start[2], end[2])
#     maxX0, maxX1, maxX2 = max(start[0], end[0]), max(start[1], end[1]), max(start[2], end[2])
#     offset0, offset1, offset2 = max(minX0 - xy_extension, 0), max(minX1 - xy_extension, 0), max(minX2 - z_extension, 0)

#     cython.declare(num_channels=cython.int)
#     num_channels = img.shape[3]

#     cython.declare(W=cython.double[:, :, :, :])
#     W = img[
#         offset2: min(maxX2 + z_extension, img.shape[0]),
#         offset0: min(maxX0 + xy_extension, img.shape[1]),
#         offset1: min(maxX1 + xy_extension, img.shape[2]),
#         :
#     ].astype(np.double)

#     # Mean smoothing, kernel size = 3
#     W = uniform_filter1d(W, axis=0)
#     W = uniform_filter1d(W, axis=1)
#     W = uniform_filter1d(W, axis=2)
#     print(W.shape)

#     # Reference intensity
#     cython.declare(base_intensity=(cython.double, cython.double, cython.double))
#     base_intensity = tuple(np.mean(
#         [W[start[2] - offset2, start[0] - offset0, start[1] - offset1, :],
#         W[end[2] - offset2, end[0] - offset0, end[1] - offset1, :]],
#         axis=(0,1,2)
#     ))
#     print("base", base_intensity)

#     # Thresholding
#     # background_intensity = np.quantile(W, 0.1)
#     # W = W - background_intensity

#     # Functions
#     # @cython.locals(pos=(cython.int, cython.int, cython.int), prev_moves=(cython.int, cython.int))
#     def get_neighbors(pos, prev_moves):
#         cython.declare(new_moves=list, i=cython.int, move=(cython.int, cython.int, cython.int))
#         new_moves = []

#         for i in range(len(possible_moves)):
#             move = possible_moves[i]
#             i_p = len(possible_moves) - i
#             if i_p == prev_moves[0] or i_p == prev_moves[1]:
#                 continue
#             new_moves.append(((pos[0]+move[0], pos[1]+move[1], pos[2]+move[2]), i))
#         return new_moves

#     # @cython.cfunc
#     # @cython.locals(pos=(cython.int, cython.int, cython.int))
#     def get_cost(pos):
#         cython.declare(intensity=cython.double[:], ti=cython.double, color_distance=cython.double, i=cython.int)

#         intensity = W[pos[2] - offset2, pos[0] - offset0, pos[1] - offset1, :]
#         ti = np.sum(intensity)
#         if ti <= 0:
#             return -1
#         color_distance = 0
#         for i in range(num_channels):
#             color_distance += (base_intensity[i] - intensity[i] / ti) ** 2
#         return color_distance + (np.sum(base_intensity) / ti) * 0.1

#     # @cython.cfunc
#     # @cython.locals(pos1=(cython.int, cython.int, cython.int), pos2=(cython.int, cython.int, cython.int))
#     def get_heuristic(pos1, pos2):
#         return manhatten_distance(pos1, pos2)

#     return astar(start, end, get_neighbors, get_cost, get_heuristic)


def mean_shift(coords, s, server_url, is_multi, xy_radius=2, z_radius=2, z_max = 2, iterations=None):
    start = [round(c) for c in s]
    res = requests.get(f"{server_url}meanshift/brainbow_test/{start[0]},{start[1]},{start[2]}")
    return [int(x) for x in res.text.split(',')]
    
