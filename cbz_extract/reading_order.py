# Original C# code from https://github.com/UglyToad/PdfPig/blob/master/src/UglyToad.PdfPig.DocumentLayoutAnalysis/ReadingOrderDetector/UnsupervisedReadingOrderDetector.cs
# was translated to Python and modified where necessary to conform with
# format of available input data

class IntervalRelations:
    Precedes = "Precedes"
    PrecedesI = "PrecedesI"
    Meets = "Meets"
    MeetsI = "MeetsI"
    Overlaps = "Overlaps"
    OverlapsI = "OverlapsI"
    Starts = "Starts"
    StartsI = "StartsI"
    During = "During"
    DuringI = "DuringI"
    Finishes = "Finishes"
    FinishesI = "FinishesI"
    Equals = "Equals"
    Unknown = "Unknown"

class TextBlock:
    def __init__(self, data, bounding_box, order):
        self.data = data
        self.BoundingBox = bounding_box
        self.order = order

class BoundingBox:
    def __init__(self, top, bottom, left, right):
        self.Top = top
        self.Bottom = bottom
        self.Left = left
        self.Right = right

def interval_relation_y(a, b, T):
    if a.BoundingBox.Bottom < b.BoundingBox.Top - T:
        return IntervalRelations.PrecedesI
    elif a.BoundingBox.Bottom >= b.BoundingBox.Top - T:
        return IntervalRelations.PrecedesI
    elif b.BoundingBox.Top - T <= a.BoundingBox.Bottom <= b.BoundingBox.Top + T:
        return IntervalRelations.MeetsI
    elif b.BoundingBox.Top - T > a.BoundingBox.Bottom > b.BoundingBox.Top + T:
        return IntervalRelations.Meets
    elif (a.BoundingBox.Top < b.BoundingBox.Top - T and
          (b.BoundingBox.Top + T < a.BoundingBox.Bottom < b.BoundingBox.Bottom - T)):
        return IntervalRelations.OverlapsI
    elif (a.BoundingBox.Top >= b.BoundingBox.Top - T and
          (b.BoundingBox.Top + T >= a.BoundingBox.Bottom >= b.BoundingBox.Bottom - T)):
        return IntervalRelations.Overlaps
    elif (b.BoundingBox.Top - T <= a.BoundingBox.Top <= b.BoundingBox.Top + T and
          a.BoundingBox.Bottom < b.BoundingBox.Bottom - T):
        return IntervalRelations.StartsI
    elif (b.BoundingBox.Top - T > a.BoundingBox.Top > b.BoundingBox.Top + T and
          a.BoundingBox.Bottom >= b.BoundingBox.Bottom - T):
        return IntervalRelations.Starts
    elif a.BoundingBox.Top > b.BoundingBox.Top + T and a.BoundingBox.Bottom < b.BoundingBox.Bottom - T:
        return IntervalRelations.DuringI
    elif a.BoundingBox.Top <= b.BoundingBox.Top + T and a.BoundingBox.Bottom >= b.BoundingBox.Bottom - T:
        return IntervalRelations.During
    elif (a.BoundingBox.Top > b.BoundingBox.Top + T and
          (b.BoundingBox.Bottom - T <= a.BoundingBox.Bottom <= b.BoundingBox.Bottom + T)):
        return IntervalRelations.FinishesI
    elif (a.BoundingBox.Top <= b.BoundingBox.Top + T and
          (b.BoundingBox.Bottom - T > a.BoundingBox.Bottom > b.BoundingBox.Bottom + T)):
        return IntervalRelations.Finishes
    elif (b.BoundingBox.Top - T <= a.BoundingBox.Top <= b.BoundingBox.Top + T and
          (b.BoundingBox.Bottom - T <= a.BoundingBox.Bottom <= b.BoundingBox.Bottom + T)):
        return IntervalRelations.Equals
    return IntervalRelations.Unknown

def interval_relation_x(a, b, T):
    if a.BoundingBox.Right < b.BoundingBox.Left - T:
        return IntervalRelations.Precedes
    elif a.BoundingBox.Right >= b.BoundingBox.Left - T:
        return IntervalRelations.PrecedesI
    elif b.BoundingBox.Left - T <= a.BoundingBox.Right <= b.BoundingBox.Left + T:
        return IntervalRelations.Meets
    elif b.BoundingBox.Left - T > a.BoundingBox.Right > b.BoundingBox.Left + T:
        return IntervalRelations.MeetsI
    elif (a.BoundingBox.Left < b.BoundingBox.Left - T and
          (b.BoundingBox.Left + T < a.BoundingBox.Right < b.BoundingBox.Right - T)):
        return IntervalRelations.Overlaps
    elif (a.BoundingBox.Left >= b.BoundingBox.Left - T and
          (b.BoundingBox.Left + T >= a.BoundingBox.Right >= b.BoundingBox.Right - T)):
        return IntervalRelations.OverlapsI
    elif (b.BoundingBox.Left - T <= a.BoundingBox.Left <= b.BoundingBox.Left + T and
          a.BoundingBox.Right < b.BoundingBox.Right - T):
        return IntervalRelations.Starts
    elif (b.BoundingBox.Left - T > a.BoundingBox.Left > b.BoundingBox.Left + T and
          a.BoundingBox.Right >= b.BoundingBox.Right - T):
        return IntervalRelations.StartsI
    elif a.BoundingBox.Left > b.BoundingBox.Left + T and a.BoundingBox.Right < b.BoundingBox.Right - T:
        return IntervalRelations.During
    elif a.BoundingBox.Left <= b.BoundingBox.Left + T and a.BoundingBox.Right >= b.BoundingBox.Right - T:
        return IntervalRelations.DuringI
    elif (a.BoundingBox.Left > b.BoundingBox.Left + T and
          (b.BoundingBox.Right - T <= a.BoundingBox.Right <= b.BoundingBox.Right + T)):
        return IntervalRelations.Finishes
    elif (a.BoundingBox.Left <= b.BoundingBox.Left + T and
          (b.BoundingBox.Right - T > a.BoundingBox.Right > b.BoundingBox.Right + T)):
        return IntervalRelations.FinishesI
    elif (b.BoundingBox.Left - T <= a.BoundingBox.Left <= b.BoundingBox.Left + T and
          (b.BoundingBox.Right - T <= a.BoundingBox.Right <= b.BoundingBox.Right + T)):
        return IntervalRelations.Equals
    return IntervalRelations.Unknown

def before_in_reading_horizontal(block_a, block_b, T):
    x_relation = interval_relation_x(block_a, block_b, T)
    y_relation = interval_relation_y(block_a, block_b, T)

    return (y_relation == IntervalRelations.Precedes or
            y_relation == IntervalRelations.Meets or
            (y_relation == IntervalRelations.Overlaps and
             (x_relation == IntervalRelations.Precedes or
              x_relation == IntervalRelations.Meets or
              x_relation == IntervalRelations.Overlaps)) or
            ((x_relation == IntervalRelations.Precedes or
              x_relation == IntervalRelations.Meets or
              x_relation == IntervalRelations.Overlaps) and
             (y_relation == IntervalRelations.Precedes or
              y_relation == IntervalRelations.Meets or
              y_relation == IntervalRelations.Overlaps or
              y_relation == IntervalRelations.Starts or
              y_relation == IntervalRelations.FinishesI or
              y_relation == IntervalRelations.Equals or
              y_relation == IntervalRelations.During or
              y_relation == IntervalRelations.DuringI or
              y_relation == IntervalRelations.Finishes or
              y_relation == IntervalRelations.StartsI or
              y_relation == IntervalRelations.OverlapsI)))

def before_in_reading_vertical(block_a, block_b, T):
    x_relation = interval_relation_x(block_a, block_b, T)
    y_relation = interval_relation_y(block_a, block_b, T)

    return (x_relation == IntervalRelations.Precedes or
            x_relation == IntervalRelations.Meets or
            (x_relation == IntervalRelations.Overlaps and
             (y_relation == IntervalRelations.Precedes or
              y_relation == IntervalRelations.Meets or
              y_relation == IntervalRelations.Overlaps)) or
            ((y_relation == IntervalRelations.Precedes or
              y_relation == IntervalRelations.Meets or
              y_relation == IntervalRelations.Overlaps) and
             (x_relation == IntervalRelations.Precedes or
              x_relation == IntervalRelations.Meets or
              x_relation == IntervalRelations.Overlaps or
              x_relation == IntervalRelations.Starts or
              x_relation == IntervalRelations.FinishesI or
              x_relation == IntervalRelations.Equals or
              x_relation == IntervalRelations.During or
              x_relation == IntervalRelations.DuringI or
              x_relation == IntervalRelations.Finishes or
              x_relation == IntervalRelations.StartsI or
              x_relation == IntervalRelations.OverlapsI)))

def before_in_reading(block_a, block_b, T):
    x_relation = interval_relation_x(block_a, block_b, T)
    y_relation = interval_relation_y(block_a, block_b, T)

    return (x_relation == IntervalRelations.Precedes or
            y_relation == IntervalRelations.Precedes or
            x_relation == IntervalRelations.Meets or
            y_relation == IntervalRelations.Meets or
            x_relation == IntervalRelations.Overlaps or
            y_relation == IntervalRelations.Overlaps)

class SpatialReasoningRules:
    ColumnWise = "ColumnWise"
    RowWise = "RowWise"
    Basic = "Basic"

def before_in_default(a, b):
    return a.order < b.order

class UnsupervisedReadingOrderDetector:
    def __init__(self, spatial_reasoning_rule=SpatialReasoningRules.ColumnWise,
                 use_default_order=True, T=5):
        self.T = T
        if spatial_reasoning_rule == SpatialReasoningRules.ColumnWise:
            if use_default_order:
                self.before_in_method = (
                    lambda a, b, t:
                        before_in_reading_vertical(a, b, t)
                        or before_in_default(a, b))
            else:
                self.before_in_method = before_in_reading_vertical
        elif spatial_reasoning_rule == SpatialReasoningRules.RowWise:
            if use_default_order:
                self.before_in_method = (
                    lambda a, b, t:
                        before_in_reading_horizontal(a, b, t)
                        or before_in_default(a, b))
            else:
                self.before_in_method = before_in_reading_horizontal
        else:
            if use_default_order:
                self.before_in_method = (
                    lambda a, b, t:
                        before_in_reading(a, b, t)
                        or before_in_default(a, b))
            else:
                self.before_in_method = before_in_reading

    def build_graph(self, text_blocks, T = None):
        if T is None:
            T = self.T
        graph = {}

        for i, block_a in enumerate(text_blocks):
            graph[i] = []
            for j, block_b in enumerate(text_blocks):
                if i == j:
                    continue
                if self.before_in_method(block_a, block_b, T):
                    graph[i].append(j)

        return graph

    def reorder(self, text_blocks, T = None):
        if T is None:
            T = self.T
        graph = self.build_graph(text_blocks, T)
        assert len(graph) == len(text_blocks)
        while graph:
            max_count = max(len(value) for value in graph.values())
            current = next((key for key, value in graph.items()
                            if len(value) == max_count),
                           None)
            
            if current is not None:
                del graph[current]

                for value in graph.values():
                    if current in value:
                        value.remove(current)

                yield current
