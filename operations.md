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

## mkdir -> ls in dir

Procedure:

Not working: "Too many levels of symbolic links"
- Es darf kein data objekt enthalten sein
- Wird nicht als directory erkannt

## touch (create empty file)

Procedure: GETATTR, LOOKUP, CREATE

touch: setting time of "$file": No such file or directory -> setattr implementation needs refinement
-> setattr needed current time (attr.st_ctime_ns) -> working

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