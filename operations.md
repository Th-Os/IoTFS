# Operations

## ls
Procedure:

Working.


## cd

Procedure:

Working.

## cat

Procedure:

Working.

## mkdir

Procedure: GETATTR, LOOKUP, MKDIR

Working.

## touch (create empty file)

Procedure: GETATTR, LOOKUP, CREATE

touch: setting time of "$file": No such file or directory -> setattr implementation needs refinement

## External Editor (e.g. nano)

Not working.

### read

Procedure:

Not Working:

nano file -> "Error reading lockfile file.swp: Not enough data read"

### write

Procedure:

Not Working:
filename.swp can't be opened